import logging
import mimetypes
import pathlib
import shutil
import tempfile
from typing import Optional

import flask

from pcapi import settings
from pcapi.connectors.beneficiaries import ubble
from pcapi.core.fraud import exceptions as fraud_exceptions
import pcapi.core.fraud.api as fraud_api
import pcapi.core.fraud.models as fraud_models
from pcapi.core.fraud.models.ubble import UbbleContent
from pcapi.core.subscription import api as subscription_api
from pcapi.core.subscription import messages as subscription_messages
from pcapi.core.users import models as users_models
from pcapi.models.beneficiary_import import BeneficiaryImportSources
import pcapi.repository as pcapi_repository
from pcapi.tasks import ubble_tasks
from pcapi.utils import requests


logger = logging.getLogger(__name__)


def update_ubble_workflow(
    fraud_check: fraud_models.BeneficiaryFraudCheck, status: fraud_models.ubble.UbbleIdentificationStatus
) -> None:
    content = ubble.get_content(fraud_check.thirdPartyId)

    if not settings.IS_PROD and fraud_api.ubble.does_match_ubble_test_email(fraud_check.user.email):
        content.birth_date = fraud_check.user.dateOfBirth.date() if fraud_check.user.dateOfBirth else None

    fraud_check.resultContent = content
    pcapi_repository.repository.save(fraud_check)

    user = fraud_check.user

    if status == fraud_models.ubble.UbbleIdentificationStatus.PROCESSING:
        user.hasCompletedIdCheck = True
        pcapi_repository.repository.save(user)
        subscription_messages.on_review_pending(user)

    elif status == fraud_models.ubble.UbbleIdentificationStatus.PROCESSED:
        try:
            fraud_check = subscription_api.handle_eligibility_difference_between_declaration_and_identity_provider(
                fraud_check
            )
            fraud_api.ubble.on_ubble_result(fraud_check)

        except fraud_exceptions.BeneficiaryFraudResultCannotBeDowngraded:
            logger.warning(
                "Trying to downgrade a beneficiary that already has been considered OK", extra={"user_id": user.id}
            )

        except Exception:  # pylint: disable=broad-except
            logger.exception("Error on Ubble fraud check result: %s", extra={"user_id": user.id})

        else:
            if fraud_check.status != fraud_models.FraudCheckStatus.OK:
                subscription_api.handle_validation_errors(user=user, reason_codes=fraud_check.reasonCodes)
                subscription_messages.on_ubble_journey_cannot_continue(user)
                return

            payload = ubble_tasks.StoreIdPictureRequest(identification_id=fraud_check.thirdPartyId)
            ubble_tasks.store_id_pictures_task.delay(payload)

            try:
                subscription_api.on_successful_application(
                    user=user,
                    source=BeneficiaryImportSources.ubble,
                    source_data=fraud_check.source_data(),
                    eligibility_type=fraud_api.get_eligibility_type(fraud_check.source_data()),
                    third_party_id=fraud_check.thirdPartyId,
                    source_id=None,
                )

            except Exception as err:  # pylint: disable=broad-except
                logger.warning(
                    "Could not save application %s, because of error: %s",
                    fraud_check.thirdPartyId,
                    err,
                )
            else:
                logger.info(
                    "Successfully created user for application %s",
                    fraud_check.thirdPartyId,
                )

    elif status == fraud_models.ubble.UbbleIdentificationStatus.ABORTED:
        fraud_check.status = fraud_models.FraudCheckStatus.CANCELED
        pcapi_repository.repository.save(fraud_check)


def start_ubble_workflow(user: users_models.User, redirect_url: str) -> str:
    content = ubble.start_identification(
        user_id=user.id,
        phone_number=user.phoneNumber,
        first_name=user.firstName,
        last_name=user.lastName,
        webhook_url=flask.url_for("Public API.ubble_webhook_update_application_status", _external=True),
        redirect_url=redirect_url,
    )
    fraud_api.ubble.start_ubble_fraud_check(user, content)
    return content.identification_url


def is_ubble_workflow_restartable(fraud_check: fraud_models.BeneficiaryFraudCheck) -> bool:
    if fraud_check.type != fraud_models.FraudCheckType.UBBLE:
        return False

    ubble_content: fraud_models.ubble_models.UbbleContent = fraud_check.source_data()
    if ubble_content.status == fraud_models.ubble_models.UbbleIdentificationStatus.INITIATED:
        return True
    return False


def archive_ubble_user_id_pictures(identification_id: str) -> bool:
    # get urls from Ubble
    fraud_check = fraud_api.ubble.get_ubble_fraud_check(identification_id)
    if not fraud_check:
        raise ValueError(f"no Ubble fraud check found with identification_id {identification_id}")

    ubble_content = ubble.get_content(fraud_check.thirdPartyId)
    download_ubble_document_pictures(ubble_content, fraud_check)

    # TODO (jsdupuis) archive each pict on remote storage (OVH or other)

    # pass boolean "are_pictures_stored" to True when they are really saved
    are_pictures_stored = False

    # update fraud_models.BeneficiaryFraudCheck.storedIdPict
    fraud_check.idPicturesStored = are_pictures_stored
    pcapi_repository.repository.save(fraud_check)

    return True


def download_ubble_document_pictures(
    ubble_content: UbbleContent, fraud_check: fraud_models.BeneficiaryFraudCheck
) -> dict:
    file_front = file_back = None

    if ubble_content.signed_image_front_url is not None:
        file_front = _download_ubble_picture(fraud_check, ubble_content.signed_image_front_url, "front")

    if ubble_content.signed_image_back_url is not None:
        file_back = _download_ubble_picture(fraud_check, ubble_content.signed_image_back_url, "back")

    return {"front": file_front, "back": file_back}


def _download_ubble_picture(
    fraud_check: fraud_models.BeneficiaryFraudCheck, url: str, face_name: str
) -> Optional[dict]:
    response = requests.get(url)

    if response.status_code != 200:
        return None

    content_type = response.headers.get("content-type")
    file_name = _generate_storable_picture_filename(fraud_check, face_name, content_type)
    file_path = pathlib.Path(tempfile.mkdtemp()) / file_name

    with open(file_path, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)

    return {"file_name": file_name, "file_path": file_path}


def _generate_storable_picture_filename(
    fraud_check: fraud_models.BeneficiaryFraudCheck, face_name: str, mime_type: Optional[str]
) -> str:
    extension = mimetypes.guess_extension(mime_type, strict=True)
    return f"{fraud_check.userId}-{fraud_check.thirdPartyId}-{face_name}{extension}"
