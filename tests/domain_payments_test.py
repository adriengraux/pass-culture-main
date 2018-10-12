from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from lxml import etree

from domain.payments import create_payment_for_booking, filter_out_already_paid_for_bookings, generate_transaction_file
from domain.reimbursement import BookingReimbursement, ReimbursementRules
from models import Offer, Venue, Booking
from models.payment import Payment
from models.payment_status import TransactionStatus
from utils.test_utils import create_booking, create_stock, create_user, create_offerer, create_payment, create_venue

XML_NAMESPACE = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'}


@pytest.mark.standalone
def test_create_payment_for_booking_with_common_information():
    # given
    user = create_user()
    stock = create_stock(price=10, available=5)
    booking = create_booking(user, stock=stock, quantity=1)
    booking.stock.offer = Offer()
    booking.stock.offer.venue = Venue()
    booking.stock.offer.venue.managingOfferer = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    booking_reimbursement = BookingReimbursement(booking, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))

    # when
    payment = create_payment_for_booking(booking_reimbursement)

    # then
    assert payment.booking == booking
    assert payment.amount == Decimal(10)
    assert payment.reimbursementRule == ReimbursementRules.PHYSICAL_OFFERS.value.description
    assert payment.comment == None
    assert payment.author == 'batch'


@pytest.mark.standalone
def test_create_payment_for_booking_when_iban_is_on_venue_should_take_payment_info_from_venue():
    # given
    user = create_user()
    stock = create_stock(price=10, available=5)
    booking = create_booking(user, stock=stock, quantity=1)
    booking.stock.offer = Offer()
    offerer = create_offerer(name='Test Offerer', iban='B135TGGEG532TG', bic='LAJR93')
    booking.stock.offer.venue = create_venue(offerer, name='Test Venue', iban='KD98765RFGHZ788', bic='LOKIJU76')
    booking.stock.offer.venue.managingOfferer = offerer
    booking_reimbursement = BookingReimbursement(booking, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))

    # when
    payment = create_payment_for_booking(booking_reimbursement)

    # then
    assert payment.iban == 'KD98765RFGHZ788'
    assert payment.bic == 'LOKIJU76'
    assert payment.recipient == 'Test Venue'


@pytest.mark.standalone
def test_create_payment_for_booking_when_no_iban_on_venue_should_take_payment_info_on_offerer():
    # given
    user = create_user()
    stock = create_stock(price=10, available=5)
    booking = create_booking(user, stock=stock, quantity=1)
    booking.stock.offer = Offer()
    offerer = create_offerer(name='Test Offerer', iban='B135TGGEG532TG', bic='LAJR93')
    booking.stock.offer.venue = create_venue(offerer, name='Test Venue', iban=None, bic=None)
    booking.stock.offer.venue.managingOfferer = offerer
    booking_reimbursement = BookingReimbursement(booking, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))

    # when
    payment = create_payment_for_booking(booking_reimbursement)

    # then
    assert payment.iban == 'B135TGGEG532TG'
    assert payment.bic == 'LAJR93'
    assert payment.recipient == 'Test Offerer'


@pytest.mark.standalone
def test_create_payment_for_booking_with_not_processable_status_when_iban_is_missing_on_offerer():
    # given
    user = create_user()
    stock = create_stock(price=10, available=5)
    booking = create_booking(user, stock=stock, quantity=1)
    booking.stock.offer = Offer()
    booking.stock.offer.venue = Venue()
    booking.stock.offer.venue.managingOfferer = create_offerer(name='Test Offerer', iban=None, bic=None)
    booking_reimbursement = BookingReimbursement(booking, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))

    # when
    payment = create_payment_for_booking(booking_reimbursement)

    # then
    assert len(payment.statuses) == 1
    assert payment.statuses[0].status == TransactionStatus.NOT_PROCESSABLE
    assert payment.statuses[0].detail == 'IBAN et BIC manquants sur l\'offreur'


@pytest.mark.standalone
def test_create_payment_for_booking_with_pending_status():
    # given
    one_second = timedelta(seconds=1)
    now = datetime.utcnow()
    user = create_user()
    stock = create_stock(price=10, available=5)
    booking = create_booking(user, stock=stock, quantity=1)
    booking.stock.offer = Offer()
    booking.stock.offer.venue = Venue()
    booking.stock.offer.venue.managingOfferer = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    booking_reimbursement = BookingReimbursement(booking, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))

    # when
    payment = create_payment_for_booking(booking_reimbursement)

    # then
    assert len(payment.statuses) == 1
    assert payment.statuses[0].status == TransactionStatus.PENDING
    assert payment.statuses[0].detail is None
    assert now - one_second < payment.statuses[0].date < now + one_second


@pytest.mark.standalone
def test_filter_out_already_paid_for_bookings():
    # Given
    booking_paid = Booking()
    booking_paid.payments = [Payment()]
    booking_reimbursement1 = BookingReimbursement(booking_paid, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))
    booking_not_paid = Booking()
    booking_reimbursement2 = BookingReimbursement(booking_not_paid, ReimbursementRules.PHYSICAL_OFFERS, Decimal(10))
    booking_reimbursements = [booking_reimbursement1, booking_reimbursement2]

    # When
    bookings_not_paid = filter_out_already_paid_for_bookings(booking_reimbursements)
    # Then
    assert len(bookings_not_paid) == 1
    assert not bookings_not_paid[0].booking.payments


@pytest.mark.standalone
def test_generate_transaction_file_has_initiating_party_in_group_header(app):
    # Given
    offerer = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [
        create_payment(Booking(), offerer, Decimal(10)),
        create_payment(Booking(), offerer, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:GrpHdr/ns:InitgPty/ns:Nm', xml) == 'pass Culture', \
        'The initiating party should be "pass Culture"'


@pytest.mark.standalone
def test_generate_transaction_file_has_control_sum_in_group_header(app):
    # Given
    offerer = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [
        create_payment(Booking(), offerer, Decimal(10)),
        create_payment(Booking(), offerer, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:GrpHdr/ns:CtrlSum', xml) == '30', \
        'The control sum should match the total amount of money to pay'


@pytest.mark.standalone
def test_generate_transaction_file_has_number_of_transactions_in_group_header(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    offerer2 = create_offerer(iban='ZEFGERBHT345VZ', bic='BGH995')
    offerer3 = create_offerer(iban=None, bic=None)
    payments = [
        create_payment(Booking(), offerer1, Decimal(10)),
        create_payment(Booking(), offerer2, Decimal(20)),
        create_payment(Booking(), offerer3, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:GrpHdr/ns:NbOfTxs', xml) == '2', \
        'The number of transactions should match the distinct number of IBANs'


@pytest.mark.standalone
def test_generate_transaction_file_has_number_of_transactions_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    offerer2 = create_offerer(iban='ZEFGERBHT345VZ', bic='BGH995')
    offerer3 = create_offerer(iban=None, bic=None)
    payments = [
        create_payment(Booking(), offerer1, Decimal(10)),
        create_payment(Booking(), offerer2, Decimal(20)),
        create_payment(Booking(), offerer3, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:NbOfTxs', xml) == '2', \
        'The number of transactions should match the distinct number of IBANs'


@pytest.mark.standalone
def test_generate_transaction_file_has_control_sum_in_payment_info(app):
    # Given
    offerer = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [
        create_payment(Booking(), offerer, Decimal(10)),
        create_payment(Booking(), offerer, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:CtrlSum', xml) == '30', \
        'The control sum should match the total amount of money to pay'


@pytest.mark.standalone
def test_generate_transaction_file_has_payment_method_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:PmtMtd', xml) == 'TRF', \
        'The payment method should be TRF because we want to transfer money'


@pytest.mark.standalone
def test_generate_transaction_file_has_service_level_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:PmtTpInf/ns:SvcLvl/ns:Cd', xml) == 'SEPA', \
        'The service level should be SEPA'


@pytest.mark.standalone
def test_generate_transaction_file_has_category_purpose_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:PmtTpInf/ns:CtgyPurp/ns:Cd', xml) == 'GOVT', \
        'The category purpose should be GOVT since we handle government subventions'


@pytest.mark.standalone
def test_generate_transaction_file_has_banque_de_france_bic_in_debtor_agent(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:DbtrAgt/ns:FinInstnId/ns:BIC', xml) == 'BDFEFRPPCCT'


@pytest.mark.standalone
def test_generate_transaction_file_has_debtor_name_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:Dbtr/ns:Nm', xml) == 'pass Culture', \
        'The name of the debtor should be "pass Culture"'


@pytest.mark.standalone
def test_generate_transaction_file_has_charge_bearer_in_payment_info(app):
    # Given
    offerer1 = create_offerer(iban='B135TGGEG532TG', bic='LAJR93')
    payments = [create_payment(Booking(), offerer1, Decimal(10))]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_node('//ns:PmtInf/ns:ChrgBr', xml) == 'SLEV', \
        'The charge bearer should be SLEV as in "following service level"'


@pytest.mark.standalone
def test_generate_transaction_file_has_iban_in_credit_transfer_transaction_info(app):
    # Given
    offerer1 = create_offerer(name='first offerer', iban='B135TGGEG532TG', bic='LAJR93')
    offerer2 = create_offerer(name='second offerer', iban='ZEFGERBHT345VZ', bic='BGH995')
    offerer3 = create_offerer(name='third offerer', iban=None, bic=None)
    payments = [
        create_payment(Booking(), offerer1, Decimal(10)),
        create_payment(Booking(), offerer2, Decimal(20)),
        create_payment(Booking(), offerer3, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_all_nodes('//ns:PmtInf/ns:CdtTrfTxInf/ns:CdtrAcct/ns:Id/ns:IBAN', xml)[0] == 'B135TGGEG532TG'
    assert find_all_nodes('//ns:PmtInf/ns:CdtTrfTxInf/ns:CdtrAcct/ns:Id/ns:IBAN', xml)[1] == 'ZEFGERBHT345VZ'


@pytest.mark.standalone
def test_generate_transaction_file_has_bic_in_credit_transfer_transaction_info(app):
    # Given
    offerer1 = create_offerer(name='first offerer', iban='B135TGGEG532TG', bic='LAJR93')
    offerer2 = create_offerer(name='second offerer', iban='ZEFGERBHT345VZ', bic='BGH995')
    offerer3 = create_offerer(name='third offerer', iban=None, bic=None)
    payments = [
        create_payment(Booking(), offerer1, Decimal(10)),
        create_payment(Booking(), offerer2, Decimal(20)),
        create_payment(Booking(), offerer3, Decimal(20))
    ]

    # When
    xml = generate_transaction_file(payments)

    # Then
    assert find_all_nodes('//ns:PmtInf/ns:CdtTrfTxInf/ns:CdtrAgt/ns:FinInstnId/ns:BIC', xml)[0] == 'LAJR93'
    assert find_all_nodes('//ns:PmtInf/ns:CdtTrfTxInf/ns:CdtrAgt/ns:FinInstnId/ns:BIC', xml)[1] == 'BGH995'


def find_node(xpath, transaction_file):
    xml = BytesIO(transaction_file.encode())
    tree = etree.parse(xml, etree.XMLParser())
    node = tree.find(xpath, namespaces=XML_NAMESPACE)
    return node.text


def find_all_nodes(xpath, transaction_file):
    xml = BytesIO(transaction_file.encode())
    tree = etree.parse(xml, etree.XMLParser())
    nodes = tree.findall(xpath, namespaces=XML_NAMESPACE)
    return [node.text for node in nodes]
