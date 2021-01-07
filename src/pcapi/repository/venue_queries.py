from pcapi.models import VenueSQLEntity


def find_by_id(venue_id: int) -> VenueSQLEntity:
    return VenueSQLEntity.query.filter_by(id=venue_id).first()


def find_by_siret(siret):
    return VenueSQLEntity.query.filter_by(siret=siret).first()


def find_by_managing_offerer_id(offerer_id: int) -> VenueSQLEntity:
    return VenueSQLEntity.query.filter_by(managingOffererId=offerer_id).first()


def find_by_offerer_id_and_is_virtual(offrer_id: int):
    return VenueSQLEntity.query.filter_by(managingOffererId=offrer_id, isVirtual=True).first()
