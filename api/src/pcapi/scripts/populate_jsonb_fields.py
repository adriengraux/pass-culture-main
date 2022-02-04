import os


os.environ.setdefault("CORS_ALLOWED_ORIGINS", "*")
os.environ.setdefault("CORS_ALLOWED_ORIGINS_NATIVE", "*")
os.environ.setdefault("CORS_ALLOWED_ORIGINS_ADAGE_IFRAME", "*")
os.environ.setdefault("DEMARCHES_SIMPLIFIEES_ENROLLMENT_PROCEDURE_ID_v2", "0")
os.environ.setdefault("DEMARCHES_SIMPLIFIEES_ENROLLMENT_PROCEDURE_ID_v3", "0")
os.environ.setdefault("JWT_SECRET_KEY", "fépachié")
os.environ.setdefault("DATABASE_URL", "postgresql://pass_culture:passq@localhost:5434/pass_culture")


from pcapi.core.mails.models.models import Email
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import OfferValidationConfig
from pcapi.flask_app import app
from pcapi.models import Model
from pcapi.models import db
from pcapi.models.product import Product


app.app_context().push()


BATCH_SIZE = 100_000  # number of ids SELECTEd from DB at once
SUB_BATCH_SIZE = 100  # number of ids UPDATEd at once
TO_BE_POPULATED = {
    Offer: {"json_field": "extraData", "jsonb_field": "jsonData"},
    Product: {"json_field": "extraData", "jsonb_field": "jsonData"},
    OfferValidationConfig: {"json_field": "specs", "jsonb_field": "specsNew"},
    Email: {"json_field": "content", "jsonb_field": "contentNew"},
}


def get_ids(model: Model, json_field: str, jsonb_field: str, limit: int) -> list[int]:
    query = (
        f"SELECT id "
        f'FROM "{model.__tablename__}" '
        f'WHERE "{json_field}" IS NOT NULL AND "{jsonb_field}" IS NULL '
        f"ORDER BY id "
        f"LIMIT {limit};"
    )
    # print(f'\t{query}')
    result = db.session.execute(query)
    return [row.id for row in result]


def populate_batch(model: Model, json_field: str, jsonb_field: str, ids: list[int]) -> None:
    query = (
        f'UPDATE "{model.__tablename__}" '
        f'SET "{jsonb_field}" = "{json_field}"::JSONB '
        f'WHERE id IN ({", ".join(map(str, ids))});'
    )
    # print(f'\t\t{query}')
    db.session.execute(query)
    db.session.execute("COMMIT;")


def extract_batches(source: list[int], size: int) -> list[list[int]]:
    batch_number = 0
    batches = []
    while batch := source[batch_number * size : (batch_number + 1) * size]:
        batches.append(batch)
        batch_number += 1
    return batches


def populate_model(model: Model, json_field: str, jsonb_field: str, batch_size: int, sub_batch_size: int) -> None:
    print(f"--- Populating model {model.__name__}: {json_field} -> {jsonb_field} [{batch_size}, {sub_batch_size}]")
    batch = 0
    while ids := get_ids(model, json_field, jsonb_field, batch_size):
        print(f"\tbatch #{batch:03}: {len(ids):06} ids returned")
        for sub_batch, sub_ids in enumerate(extract_batches(ids, sub_batch_size)):
            populate_batch(model, json_field, jsonb_field, sub_ids)
            print(f"\t\tsub batch #{batch:03}-{sub_batch:04}: {len(sub_ids)} ids populated")
        batch += 1


def main():
    for model, fields in TO_BE_POPULATED.items():
        populate_model(model, fields["json_field"], fields["jsonb_field"], BATCH_SIZE, SUB_BATCH_SIZE)


# TODO: rendre tout ce bordel asynchrone (parralleliser les requêtes SQL UPDATE)
if __name__ == "__main__":
    main()
