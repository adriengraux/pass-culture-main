import logging

from pydantic import BaseModel

from pcapi import settings
from pcapi.core.subscription.ubble import api as ubble_subscription_api
from pcapi.tasks.decorator import task


logger = logging.getLogger(__name__)

UBBLE_STORE_ID_CHECK_PICTURES_QUEUE_NAME = settings.GCP_UBBLE_STORE_ID_CHECK_PICTURES_QUEUE_NAME


class StoreIdPictureRequest(BaseModel):
    identification_id: str


@task(UBBLE_STORE_ID_CHECK_PICTURES_QUEUE_NAME, "/ubble/store_id_pictures")
def store_id_pictures_task(payload: StoreIdPictureRequest) -> None:
    try:
        ubble_subscription_api.archive_ubble_user_id_pictures(payload.identification_id)
    except Exception as err:  # pylint: disable=broad-except
        logger.error(str(err))
