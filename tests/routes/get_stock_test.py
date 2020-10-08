from pcapi.repository import repository
import pytest
from tests.conftest import TestClient
from pcapi.model_creators.generic_creators import create_user, create_offerer, create_venue
from pcapi.model_creators.specific_creators import create_stock_with_event_offer
from pcapi.utils.human_ids import humanize


class Get:
    class Returns200:
        @pytest.mark.usefixtures("db_session")
        def when_user_is_admin(self, app):
            # given
            user = create_user(can_book_free_offers=False, email='test@email.com', is_admin=True)
            offerer = create_offerer()
            venue = create_venue(offerer)
            stock = create_stock_with_event_offer(offerer, venue, price=10, quantity=10)
            repository.save(user, stock)
            humanized_stock_id = humanize(stock.id)

            # when
            request = TestClient(app.test_client()).with_auth('test@email.com') \
                .get('/stocks/' + humanized_stock_id)
            # then
            assert request.status_code == 200
            assert request.json['quantity'] == 10
            assert request.json['price'] == 10

    class Returns404:
        @pytest.mark.usefixtures("db_session")
        def when_stock_is_soft_deleted(self, app):
            # given
            user = create_user(can_book_free_offers=False, email='test@email.com', is_admin=True)
            offerer = create_offerer()
            venue = create_venue(offerer)
            stock = create_stock_with_event_offer(offerer, venue, price=10, quantity=10, is_soft_deleted=True)
            repository.save(user, stock)
            humanized_stock_id = humanize(stock.id)

            # when
            request = TestClient(app.test_client()).with_auth('test@email.com') \
                .get('/stocks/' + humanized_stock_id)

            # then
            assert request.status_code == 404
