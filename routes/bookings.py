""" bookings routes """
from flask import current_app as app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import InternalError

from domain.expenses import get_expenses
from models import ApiErrors, Booking, PcObject, Stock, RightsType
from models.pc_object import serialize
from repository import booking_queries
from utils.human_ids import dehumanize, humanize
from utils.includes import BOOKING_INCLUDES
from utils.mailing import send_booking_recap_emails, send_booking_confirmation_email_to_user
from utils.rest import expect_json_data, ensure_current_user_has_rights
from utils.token import random_token
from validation.bookings import check_has_stock_id, check_has_quantity, check_existing_stock, check_can_book_free_offer, \
    check_offer_is_active, check_stock_booking_limit_date, check_expenses_limits, \
    check_user_is_logged_in_or_email_is_provided, \
    check_booking_not_cancelled, check_booking_not_already_validated


@app.route('/bookings', methods=['GET'])
@login_required
def get_bookings():
    bookings = Booking.query.filter_by(userId=current_user.id).all()
    return jsonify([booking._asdict(include=BOOKING_INCLUDES)
                    for booking in bookings]), 200


@app.route('/bookings/<booking_id>', methods=['GET'])
@login_required
def get_booking(booking_id):
    booking = Booking.query.filter_by(id=dehumanize(booking_id)).first_or_404()
    return jsonify(booking._asdict(include=BOOKING_INCLUDES)), 200


@app.route('/bookings', methods=['POST'])
@login_required
@expect_json_data
def create_booking():
    stock_id = request.json.get('stockId')
    recommendation_id = request.json.get('recommendationId')
    quantity = request.json.get('quantity')

    try:
        check_has_stock_id(stock_id)
        check_has_quantity(quantity)
    except ApiErrors as api_errors:
        return jsonify(api_errors.errors), 400

    stock = Stock.queryNotSoftDeleted().filter_by(id=dehumanize(stock_id)).first()
    managing_offerer = stock.resolvedOffer.venue.managingOfferer

    try:
        check_existing_stock(stock)
        check_can_book_free_offer(stock, current_user)
        check_offer_is_active(stock, managing_offerer)
        check_stock_booking_limit_date(stock)
    except ApiErrors as api_errors:
        return jsonify(api_errors.errors), 400

    new_booking = Booking(from_dict={
        'stockId': stock_id,
        'amount': stock.price,
        'token': random_token(),
        'userId': humanize(current_user.id),
        'quantity': quantity,
        'recommendationId': recommendation_id if recommendation_id else None
    })

    expenses = get_expenses(current_user)

    try:
        check_expenses_limits(expenses, new_booking, stock)
    except ApiErrors as api_errors:
        return jsonify(api_errors.errors), 400

    try:
        PcObject.check_and_save(new_booking)
    except InternalError as internal_error:
        api_errors = ApiErrors()
        if 'tooManyBookings' in str(internal_error.orig):
            api_errors.addError('global', 'la quantité disponible pour cette offre est atteinte')
        elif 'insufficientFunds' in str(internal_error.orig):
            api_errors.addError('insufficientFunds', 'l\'utilisateur ne dispose pas de fonds suffisants pour '
                                                     'effectuer une réservation.')
        return jsonify(api_errors.errors), 400

    new_booking_stock = Stock.query.get(new_booking.stockId)
    send_booking_recap_emails(new_booking_stock, new_booking)
    send_booking_confirmation_email_to_user(new_booking)

    return jsonify(new_booking._asdict(include=BOOKING_INCLUDES)), 201


@app.route('/bookings/<booking_id>', methods=['DELETE'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=dehumanize(booking_id)).first_or_404()

    if not booking.user == current_user \
            and not current_user.hasRights(RightsType.editor,
                                           booking.stock.resolvedOffer.venue.managingOffererId):
        return "Vous n'avez pas le droit d'annuler cette réservation", 403

    booking.isCancelled = True
    PcObject.check_and_save(booking)

    return jsonify(booking._asdict(include=BOOKING_INCLUDES)), 200

@app.route('/bookings/token/<token>', methods=["GET"])
def get_booking_by_token(token):
    email = request.args.get('email', None)
    offer_id = dehumanize(request.args.get('offer_id', None))

    check_user_is_logged_in_or_email_is_provided(current_user, email)

    booking = booking_queries.find_by_token(token, email, offer_id)
    offer_name = booking.stock.resolvedOffer.eventOrThing.name
    date = None
    if booking.stock.eventOccurrence:
        date = serialize(booking.stock.eventOccurrence.beginningDatetime)
    offerer_id = booking.stock.resolvedOffer.venue.managingOffererId

    current_user_can_validate_bookings = current_user.is_authenticated and current_user.hasRights(RightsType.editor, offerer_id)
    if current_user_can_validate_bookings:
        response = {'bookingId': booking.id, 'email': booking.user.email, 'userName': booking.user.publicName, 'offerName': offer_name, 'date': date,
                    'isValidated': booking.isValidated}
        return jsonify(response), 200
    return '', 204


@app.route('/bookings/token/<token>', methods=["PATCH"])
def patch_booking_by_token(token):
    email = request.args.get('email', None)
    offer_id = dehumanize(request.args.get('offer_id', None))
    booking = booking_queries.find_by_token(token, email, offer_id)
    offerer_id = booking.stock.resolvedOffer.venue.managingOffererId
    if not email:
        ensure_current_user_has_rights(RightsType.editor, offerer_id)
    check_booking_not_cancelled(booking)
    check_booking_not_already_validated(booking)
    booking.populateFromDict({'isValidated': True})
    PcObject.check_and_save(booking)

    return '', 200
