from pcapi.infrastructure.repository.beneficiary_bookings.beneficiary_bookings_sql_repository import (
    BeneficiaryBookingsSQLRepository,
)
from pcapi.infrastructure.repository.favorite.favorite_sql_repository import FavoriteSQLRepository
from pcapi.infrastructure.repository.pro_offerers.paginated_offerers_sql_repository import (
    PaginatedOfferersSQLRepository,
)
from pcapi.infrastructure.repository.stock_provider.stock_provider_fnac import StockProviderFnacRepository
from pcapi.infrastructure.repository.stock_provider.stock_provider_libraires import StockProviderLibrairesRepository
from pcapi.infrastructure.repository.stock_provider.stock_provider_praxiel import StockProviderPraxielRepository
from pcapi.infrastructure.repository.stock_provider.stock_provider_titelive import StockProviderTiteLiveRepository
from pcapi.infrastructure.repository.venue.venue_label.venue_label_sql_repository import VenueLabelSQLRepository
from pcapi.infrastructure.repository.venue.venue_with_basic_information.venue_with_basic_information_sql_repository import (
    VenueWithBasicInformationSQLRepository,
)
from pcapi.infrastructure.repository.venue.venue_with_offerer_name.venue_with_offerer_name_sql_repository import (
    VenueWithOffererNameSQLRepository,
)
from pcapi.use_cases.get_bookings_for_beneficiary import GetBookingsForBeneficiary
from pcapi.use_cases.get_venue_labels import GetVenueLabels
from pcapi.use_cases.get_venues_by_pro_user import GetVenuesByProUser
from pcapi.use_cases.list_favorites_of_beneficiary import ListFavoritesOfBeneficiary
from pcapi.use_cases.list_offerers_for_pro_user import ListOfferersForProUser


beneficiary_bookings_repository = BeneficiaryBookingsSQLRepository()
favorite_repository = FavoriteSQLRepository()
venue_label_repository = VenueLabelSQLRepository()
venue_identifier_repository = VenueWithBasicInformationSQLRepository()
venue_with_offerer_informations_repository = VenueWithOffererNameSQLRepository()
paginated_offerers_repository = PaginatedOfferersSQLRepository()

api_libraires_stocks = StockProviderLibrairesRepository()
api_fnac_stocks = StockProviderFnacRepository()
api_titelive_stocks = StockProviderTiteLiveRepository()
api_praxiel_stocks = StockProviderPraxielRepository()

# Usecases
get_venue_labels = GetVenueLabels(venue_label_repository=venue_label_repository)

get_all_venues_by_pro_user = GetVenuesByProUser(venue_repository=venue_with_offerer_informations_repository)

list_favorites_of_beneficiary = ListFavoritesOfBeneficiary(favorite_repository=favorite_repository)

get_bookings_for_beneficiary = GetBookingsForBeneficiary(
    beneficiary_bookings_repository=beneficiary_bookings_repository
)

list_offerers_for_pro_user = ListOfferersForProUser(paginated_offerers_repository=paginated_offerers_repository)
