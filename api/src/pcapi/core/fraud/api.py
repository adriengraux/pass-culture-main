import datetime
import logging
import re
import typing

import pydantic
import sqlalchemy

from pcapi.core.users import constants
from pcapi.core.users import models as users_models
from pcapi.core.users import utils as users_utils
from pcapi.models import db
from pcapi.models.feature import FeatureToggle
from pcapi.repository import repository
from pcapi.repository.user_queries import matching

from . import exceptions
from . import models
from .dms import api as dms_api
from .ubble import api as ubble_api
from .ubble import models as ubble_fraud_models


logger = logging.getLogger(__name__)

FRAUD_RESULT_REASON_SEPARATOR = ";"

USER_PROFILING_RISK_MAPPING = {
    models.UserProfilingRiskRating.TRUSTED: models.FraudStatus.OK,
    models.UserProfilingRiskRating.NEUTRAL: models.FraudStatus.OK,
    models.UserProfilingRiskRating.LOW: models.FraudStatus.OK,
    models.UserProfilingRiskRating.MEDIUM: models.FraudStatus.SUSPICIOUS,
    models.UserProfilingRiskRating.HIGH: models.FraudStatus.KO,
}

USER_PROFILING_FRAUD_CHECK_STATUS_RISK_MAPPING = {
    models.UserProfilingRiskRating.TRUSTED: models.FraudCheckStatus.OK,
    models.UserProfilingRiskRating.NEUTRAL: models.FraudCheckStatus.OK,
    models.UserProfilingRiskRating.LOW: models.FraudCheckStatus.OK,
    models.UserProfilingRiskRating.MEDIUM: models.FraudCheckStatus.SUSPICIOUS,
    models.UserProfilingRiskRating.HIGH: models.FraudCheckStatus.KO,
}


def on_educonnect_result(
    user: users_models.User, educonnect_content: models.EduconnectContent
) -> models.BeneficiaryFraudCheck:
    eligibility_type = educonnect_content.get_eligibility_type()

    fraud_check = models.BeneficiaryFraudCheck.query.filter(
        models.BeneficiaryFraudCheck.user == user,
        models.BeneficiaryFraudCheck.type == models.FraudCheckType.EDUCONNECT,
        models.BeneficiaryFraudCheck.eligibilityType == eligibility_type,
    ).one_or_none()

    if fraud_check:
        fraud_check.thirdPartyId = str(educonnect_content.educonnect_id)
        fraud_check.resultContent = educonnect_content.dict()
    else:
        fraud_check = models.BeneficiaryFraudCheck(
            user=user,
            type=models.FraudCheckType.EDUCONNECT,
            thirdPartyId=str(educonnect_content.educonnect_id),
            resultContent=educonnect_content.dict(),
            eligibilityType=eligibility_type,
        )
    on_identity_fraud_check_result(user, fraud_check)
    repository.save(fraud_check)
    return fraud_check


def on_dms_fraud_result(
    user: users_models.User,
    dms_content: models.DMSContent,
) -> models.BeneficiaryFraudCheck:

    eligibility_type = dms_content.get_eligibility_type()
    fraud_check = dms_api.get_fraud_check(user, str(dms_content.application_id))
    if not fraud_check:
        logger.warning("DMS fraud check from user %d not previously created", user.id)
        fraud_check = models.BeneficiaryFraudCheck(
            user=user,
            type=models.FraudCheckType.DMS,
            thirdPartyId=str(dms_content.application_id),
            resultContent=dms_content.dict(),
            eligibilityType=eligibility_type,
            status=models.FraudCheckStatus.PENDING,
        )
    else:
        fraud_check.resultContent = dms_content.dict()
        if fraud_check.eligibilityType != eligibility_type:
            logger.info("User changed his eligibility in DMS application", extra={"user_id": user.id})
            fraud_check.eligibilityType = eligibility_type
    on_identity_fraud_check_result(user, fraud_check)
    repository.save(fraud_check)

    return fraud_check


def admin_update_identity_fraud_check_result(
    user: users_models.User, id_piece_number: str
) -> typing.Union[models.BeneficiaryFraudCheck, None]:
    # Do not filter on eligibilityType here, a manual action validates the last one, either 15-17 or 18
    fraud_check = (
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.userId == user.id,
            models.BeneficiaryFraudCheck.type.in_(
                [
                    models.FraudCheckType.JOUVE,
                    models.FraudCheckType.DMS,
                ]
            ),
        )
        .order_by(models.BeneficiaryFraudCheck.dateCreated.desc())
        .first()
    )
    if not fraud_check:
        return None
    content = fraud_check.source_data()
    if fraud_check.type == models.FraudCheckType.JOUVE:
        content.bodyPieceNumber = id_piece_number
        content.bodyPieceNumberCtrl = "OK"
        content.bodyPieceNumberLevel = 100
    if fraud_check.type == models.FraudCheckType.DMS:
        content.id_piece_number = id_piece_number
    fraud_check.resultContent = content.dict()
    repository.save(fraud_check)
    return fraud_check


def educonnect_fraud_checks(
    user: users_models.User, beneficiary_fraud_check: models.BeneficiaryFraudCheck
) -> list[models.FraudItem]:
    educonnect_content = beneficiary_fraud_check.source_data()
    fraud_items = []
    fraud_items.append(_underage_user_fraud_item(educonnect_content.get_birth_date()))
    fraud_items.append(_duplicate_ine_hash_fraud_item(educonnect_content.ine_hash, user.id))
    if FeatureToggle.ENABLE_INE_WHITELIST_FILTER.is_active():
        fraud_items.append(_whitelisted_ine_fraud_item(educonnect_content.ine_hash))

    return fraud_items


def dms_fraud_checks(
    user: users_models.User, beneficiary_fraud_check: models.BeneficiaryFraudCheck
) -> list[models.FraudItem]:
    fraud_items = []
    fraud_items.append(
        duplicate_id_piece_number_fraud_item(user, beneficiary_fraud_check.source_data().get_id_piece_number())
    )
    return fraud_items


def on_identity_fraud_check_result(
    user: users_models.User,
    beneficiary_fraud_check: models.BeneficiaryFraudCheck,
) -> list[models.FraudItem]:
    fraud_items: list[models.FraudItem] = []

    if beneficiary_fraud_check.type == models.FraudCheckType.UBBLE:
        fraud_items += ubble_api.ubble_fraud_checks(user, beneficiary_fraud_check)

    elif beneficiary_fraud_check.type == models.FraudCheckType.DMS:
        fraud_items += dms_fraud_checks(user, beneficiary_fraud_check)

    elif beneficiary_fraud_check.type == models.FraudCheckType.EDUCONNECT:
        fraud_items += educonnect_fraud_checks(user, beneficiary_fraud_check)

    else:
        raise Exception("The fraud_check type is not known")

    content: models.IdentityCheckContent = beneficiary_fraud_check.source_data()
    content_first_name = content.get_first_name()
    content_last_name = content.get_last_name()
    content_birth_date = content.get_birth_date()
    content_eligibility_type = content.get_eligibility_type()

    # Check for duplicate only when Id Check returns identity details
    if content_first_name and content_last_name and content_birth_date:
        fraud_items.append(
            _duplicate_user_fraud_item(
                first_name=content_first_name,
                last_name=content_last_name,
                birth_date=content_birth_date,
                excluded_user_id=user.id,
            )
        )

    if content_birth_date:
        fraud_items.append(_check_user_eligibility(user, content_eligibility_type))

    fraud_items.append(_check_user_has_no_active_deposit(user, content_eligibility_type))
    fraud_items.append(_check_user_email_is_validated(user))

    return validate_frauds(fraud_items, beneficiary_fraud_check)


def validate_id_piece_number_format_fraud_item(id_piece_number: typing.Optional[str]) -> models.FraudItem:
    if not id_piece_number or not id_piece_number.strip():
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail="Le numéro de la pièce d'identité est vide",
            reason_code=models.FraudReasonCode.EMPTY_ID_PIECE_NUMBER,
        )

    regexp = "|".join(
        (
            r"(^\d{18}$)",  # ID Algérienne
            r"(^[\w]{8,12}|[\s\w]{14}$)",  # ID Europeene ID Française
            r"(^\w{1}\d{6}$)",  # ID Tunisienne
            r"(^\w{1}\ *\d{8}$)",  # ID Turque
            r"(^\w{2}\ *\d{7}$)",  # Ancienne ID Italienne
            r"(^\d{3}\-\d{7}\-\d{2}$)",  # ID Belge
            r"(^\d{7}$)",  # ID Congolaise, Camerounaise, Mauricienne
        )
    )

    if not re.fullmatch(
        regexp,
        id_piece_number,
    ):
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail="Le format du numéro de la pièce d'identité n'est pas valide",
            reason_code=models.FraudReasonCode.INVALID_ID_PIECE_NUMBER,
        )
    return models.FraudItem(status=models.FraudStatus.OK, detail="Le numéro de pièce d'identité est valide")


def _duplicate_user_fraud_item(
    first_name: str, last_name: str, birth_date: datetime.date, excluded_user_id: int
) -> models.FraudItem:
    duplicate_user = users_models.User.query.filter(
        matching(users_models.User.firstName, first_name)
        & (matching(users_models.User.lastName, last_name))
        & (sqlalchemy.func.DATE(users_models.User.dateOfBirth) == birth_date)
        & (users_models.User.is_beneficiary == True)
        & (users_models.User.id != excluded_user_id)
    ).first()

    if duplicate_user:
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail=f"Duplicat de l'utilisateur {duplicate_user.id}",
            reason_code=models.FraudReasonCode.DUPLICATE_USER,
        )

    return models.FraudItem(status=models.FraudStatus.OK, detail="Utilisateur non dupliqué")


def duplicate_id_piece_number_fraud_item(user: users_models.User, document_id_number: str) -> models.FraudItem:
    duplicate_user = users_models.User.query.filter(
        users_models.User.id != user.id, users_models.User.idPieceNumber == document_id_number
    ).first()

    if duplicate_user:
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail=f"La pièce d'identité n°{document_id_number} est déjà prise par l'utilisateur {duplicate_user.id}",
            reason_code=models.FraudReasonCode.DUPLICATE_ID_PIECE_NUMBER,
        )

    return models.FraudItem(status=models.FraudStatus.OK, detail="La pièce d'identité n'est pas déjà utilisée")


def _duplicate_ine_hash_fraud_item(ine_hash: str, excluded_user_id: int) -> models.FraudItem:
    duplicate_user = users_models.User.query.filter(
        users_models.User.ineHash == ine_hash, users_models.User.id != excluded_user_id
    ).first()

    if duplicate_user:
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail=f"L'INE {ine_hash} est déjà pris par l'utilisateur {duplicate_user.id}",
            reason_code=models.FraudReasonCode.DUPLICATE_INE,
        )

    return models.FraudItem(status=models.FraudStatus.OK, detail="L'INE n'est pas déjà pris")


def _whitelisted_ine_fraud_item(ine_hash: str) -> models.FraudItem:
    is_ine_whitelisted = db.session.query(models.IneHashWhitelist.query.filter_by(ine_hash=ine_hash).exists()).scalar()

    if not is_ine_whitelisted:
        return models.FraudItem(
            status=models.FraudStatus.SUSPICIOUS,
            detail=f"L'INE {ine_hash} n'est pas whitelisté",
            reason_code=models.FraudReasonCode.INE_NOT_WHITELISTED,
        )

    return models.FraudItem(status=models.FraudStatus.OK, detail="L'INE est whitelisté")


def _check_user_has_no_active_deposit(
    user: users_models.User, eligibility: users_models.EligibilityType
) -> models.FraudItem:
    if user.has_active_deposit:
        return models.FraudItem(
            status=models.FraudStatus.KO,
            detail=(
                "L’utilisateur est déjà bénéfiaire, avec un portefeuille non expiré. "
                f"Il ne peut pas prétendre au pass culture {'15-17 ans' if eligibility == users_models.EligibilityType.UNDERAGE else '18 ans'}"
            ),
            reason_code=models.FraudReasonCode.ALREADY_HAS_ACTIVE_DEPOSIT,
        )
    return models.FraudItem(status=models.FraudStatus.OK, detail="L'utilisateur n'a pas déjà un deposit actif")


def _check_user_eligibility(
    user: users_models.User, eligibility: typing.Optional[users_models.EligibilityType]
) -> models.FraudItem:
    from pcapi.core.users import api as users_api

    if not eligibility:
        return models.FraudItem(
            status=models.FraudStatus.KO,
            detail="L'âge indiqué dans le dossier indique que l'utilisateur n'est pas éligible",
            reason_code=models.FraudReasonCode.NOT_ELIGIBLE,
        )

    if not users_api.is_eligible_for_beneficiary_upgrade(user, eligibility):
        return models.FraudItem(
            status=models.FraudStatus.KO,
            detail=(f"L’utilisateur est déjà bénéfiaire du pass {eligibility.name}"),
            reason_code=models.FraudReasonCode.ALREADY_BENEFICIARY,
        )

    return models.FraudItem(
        status=models.FraudStatus.OK, detail="L'utilisateur est éligible à un nouveau statut bénéficiaire"
    )


def _check_user_email_is_validated(user: users_models.User) -> models.FraudItem:
    if not user.isEmailValidated:
        return models.FraudItem(
            status=models.FraudStatus.KO,
            detail="L'email de l'utilisateur n'est pas validé",
            reason_code=models.FraudReasonCode.EMAIL_NOT_VALIDATED,
        )
    return models.FraudItem(status=models.FraudStatus.OK, detail="L'email est validé")


def _underage_user_fraud_item(birth_date: datetime.date) -> models.FraudItem:
    age = users_utils.get_age_from_birth_date(birth_date)
    if age in constants.ELIGIBILITY_UNDERAGE_RANGE:
        return models.FraudItem(
            status=models.FraudStatus.OK,
            detail=f"L'âge de l'utilisateur est valide ({age} ans).",
        )
    return models.FraudItem(
        status=models.FraudStatus.KO,
        detail=f"L'âge de l'utilisateur est invalide ({age} ans). Il devrait être parmi {constants.ELIGIBILITY_UNDERAGE_RANGE}",
        reason_code=models.FraudReasonCode.AGE_NOT_VALID,
    )


def on_user_profiling_result(
    user: users_models.User, profiling_infos: models.UserProfilingFraudData
) -> models.BeneficiaryFraudCheck:
    risk_rating = profiling_infos.risk_rating
    fraud_check_status = USER_PROFILING_FRAUD_CHECK_STATUS_RISK_MAPPING[risk_rating]
    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=models.FraudCheckType.USER_PROFILING,
        thirdPartyId=profiling_infos.session_id,
        resultContent=profiling_infos,
        status=fraud_check_status,
        eligibilityType=user.eligibility,
    )
    repository.save(fraud_check)
    on_user_profiling_check_result(user, risk_rating)
    return fraud_check


def on_user_profiling_check_result(
    user: users_models.User,
    risk_rating: models.UserProfilingRiskRating,
) -> None:
    user_profiling_status = USER_PROFILING_RISK_MAPPING[risk_rating]
    if not user_profiling_status == models.FraudStatus.OK:
        user.validate_profiling_failed()

        from pcapi.core.subscription import messages as subscription_messages

        subscription_messages.on_user_subscription_journey_stopped(user)
    else:
        user.validate_profiling()

    repository.save(user)


def get_source_data(user: users_models.User) -> pydantic.BaseModel:
    mapped_class = {models.FraudCheckType.DMS: models.DMSContent, models.FraudCheckType.JOUVE: models.JouveContent}
    fraud_check = (
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.userId == user.id,
            models.BeneficiaryFraudCheck.type.in_([models.FraudCheckType.JOUVE, models.FraudCheckType.DMS]),
        )
        .order_by(models.BeneficiaryFraudCheck.dateCreated.desc())
        .first()
    )
    return mapped_class[fraud_check.type](**fraud_check.resultContent)


def create_failed_phone_validation_fraud_check(
    user: users_models.User, fraud_check_data: models.PhoneValidationFraudData
) -> models.BeneficiaryFraudCheck:
    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=models.FraudCheckType.PHONE_VALIDATION,
        thirdPartyId=f"PC-{user.id}",
        resultContent=fraud_check_data,
        eligibilityType=user.eligibility,
        status=models.FraudCheckStatus.KO,
    )

    repository.save(fraud_check)
    return fraud_check


def handle_phone_already_exists(user: users_models.User, phone_number: str) -> models.BeneficiaryFraudCheck:
    orig_user_id = (
        users_models.User.query.filter(
            users_models.User.phoneNumber == phone_number, users_models.User.is_phone_validated
        )
        .one()
        .id
    )
    reason = f"Le numéro est déjà utilisé par l'utilisateur {orig_user_id}"
    fraud_check_data = models.PhoneValidationFraudData(
        source=models.InternalReviewSource.PHONE_ALREADY_EXISTS, message=reason, phone_number=phone_number
    )

    return create_failed_phone_validation_fraud_check(user, fraud_check_data)


def handle_blacklisted_sms_recipient(user: users_models.User, phone_number: str) -> models.BeneficiaryFraudCheck:
    reason = "Le numéro saisi est interdit"
    fraud_check_data = models.PhoneValidationFraudData(
        source=models.InternalReviewSource.BLACKLISTED_PHONE_NUMBER, message=reason, phone_number=phone_number
    )

    return create_failed_phone_validation_fraud_check(user, fraud_check_data)


def handle_sms_sending_limit_reached(user: users_models.User) -> None:
    reason = "Le nombre maximum de sms envoyés est atteint"
    fraud_check_data = models.PhoneValidationFraudData(
        source=models.InternalReviewSource.SMS_SENDING_LIMIT_REACHED,
        message=reason,
        phone_number=user.phoneNumber,
    )

    create_failed_phone_validation_fraud_check(user, fraud_check_data)


def handle_phone_validation_attempts_limit_reached(user: users_models.User, attempts_count: int) -> None:
    reason = f"Le nombre maximum de tentatives de validation est atteint: {attempts_count}"
    fraud_check_data = models.PhoneValidationFraudData(
        source=models.InternalReviewSource.PHONE_VALIDATION_ATTEMPTS_LIMIT_REACHED,
        message=reason,
        phone_number=user.phoneNumber,
    )

    create_failed_phone_validation_fraud_check(user, fraud_check_data)


def validate_frauds(
    fraud_items: list[models.FraudItem],
    fraud_check: models.BeneficiaryFraudCheck,
) -> list[models.FraudItem]:
    if all(fraud_item.status == models.FraudStatus.OK for fraud_item in fraud_items):
        fraud_check_status = models.FraudCheckStatus.OK
    elif any(fraud_item.status == models.FraudStatus.KO for fraud_item in fraud_items):
        fraud_check_status = models.FraudCheckStatus.KO
    else:
        fraud_check_status = models.FraudCheckStatus.SUSPICIOUS

    reason = f" {FRAUD_RESULT_REASON_SEPARATOR} ".join(
        fraud_item.detail for fraud_item in fraud_items if fraud_item.status != models.FraudStatus.OK
    )
    reason_codes = [
        fraud_item.reason_code
        for fraud_item in fraud_items
        if fraud_item.status != models.FraudStatus.OK and fraud_item.reason_code is not None
    ]

    fraud_check.status = fraud_check_status
    fraud_check.reason = reason
    fraud_check.reasonCodes = reason_codes
    repository.save(fraud_check)

    return fraud_items


def has_user_pending_identity_check(user: users_models.User) -> bool:
    return db.session.query(
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.user == user,
            models.BeneficiaryFraudCheck.status == models.FraudCheckStatus.PENDING,
            models.BeneficiaryFraudCheck.type.in_(models.IDENTITY_CHECK_TYPES),
            models.BeneficiaryFraudCheck.eligibilityType == user.eligibility,
            models.BeneficiaryFraudCheck.resultContent["status"]
            != models.ubble_fraud_models.UbbleIdentificationStatus.INITIATED,
        ).exists()
    ).scalar()


def has_user_performed_identity_check(user: users_models.User) -> bool:
    return db.session.query(
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.user == user,
            models.BeneficiaryFraudCheck.status.is_distinct_from(models.FraudCheckStatus.CANCELED),
            models.BeneficiaryFraudCheck.status.is_distinct_from(models.FraudCheckStatus.STARTED),
            models.BeneficiaryFraudCheck.type.in_(models.IDENTITY_CHECK_TYPES),
        ).exists()
    ).scalar()


def has_passed_educonnect(user: users_models.User) -> bool:
    return db.session.query(
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.user == user,
            models.BeneficiaryFraudCheck.status == models.FraudCheckStatus.OK,
            models.BeneficiaryFraudCheck.type == models.FraudCheckType.EDUCONNECT,
        ).exists()
    ).scalar()


def is_risky_user_profile(user: users_models.User) -> bool:
    # No need to filter on eligibilityType ; profiling is performed only for AGE18 users.
    user_profiling = (
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.user == user,
            models.BeneficiaryFraudCheck.type == models.FraudCheckType.USER_PROFILING,
        )
        .order_by(models.BeneficiaryFraudCheck.dateCreated.desc())
        .first()
    )

    if user_profiling and user_profiling.source_data().risk_rating == models.UserProfilingRiskRating.HIGH:
        return True

    if not (user_profiling or FeatureToggle.ALLOW_EMPTY_USER_PROFILING.is_active()):
        # unprofiled user and forbidden empty profiling -> risky
        return True

    return False


def start_fraud_check(
    user: users_models.User,
    application_id: str,
    source_data: typing.Union[models.DMSContent, ubble_fraud_models.UbbleContent],
) -> models.BeneficiaryFraudCheck:

    source_type = models.FRAUD_CONTENT_MAPPING[type(source_data)]

    fraud_check = models.BeneficiaryFraudCheck.query.filter(
        models.BeneficiaryFraudCheck.user == user,
        models.BeneficiaryFraudCheck.type == source_type,
        models.BeneficiaryFraudCheck.thirdPartyId == application_id,
    ).one_or_none()

    if fraud_check:
        raise exceptions.ApplicationValidationAlreadyStarted()

    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=source_type,
        thirdPartyId=application_id,
        resultContent=source_data.dict(),
        status=models.FraudCheckStatus.PENDING,
        eligibilityType=source_data.get_eligibility_type(),
    )

    repository.save(fraud_check)

    return fraud_check


def mark_fraud_check_failed(
    user: users_models.User,
    application_id: str,
    source_data: typing.Union[models.DMSContent, ubble_fraud_models.UbbleContent],
    reasons: list[models.FraudItem],
) -> models.BeneficiaryFraudCheck:
    source_type = models.FRAUD_CONTENT_MAPPING[type(source_data)]
    fraud_check = models.BeneficiaryFraudCheck.query.filter(
        models.BeneficiaryFraudCheck.user == user,
        models.BeneficiaryFraudCheck.type == source_type,
        models.BeneficiaryFraudCheck.thirdPartyId == application_id,
        ~models.BeneficiaryFraudCheck.status.in_([models.FraudCheckStatus.OK, models.FraudCheckStatus.KO]),
    ).one_or_none()

    if not fraud_check:
        fraud_check = models.BeneficiaryFraudCheck(
            user=user,
            type=source_type,
            thirdPartyId=application_id,
            resultContent=source_data.dict(),
            status=models.FraudCheckStatus.PENDING,
            eligibilityType=source_data.get_eligibility_type(),
        )

    fraud_check.status = models.FraudCheckStatus.KO
    fraud_check.reasonCodes = reasons
    repository.save(fraud_check)
    return fraud_check


def create_honor_statement_fraud_check(
    user: users_models.User, origin: str, eligibility_type: typing.Optional[users_models.EligibilityType] = None
) -> None:
    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=models.FraudCheckType.HONOR_STATEMENT,
        status=models.FraudCheckStatus.OK,
        reason=origin,
        thirdPartyId=f"internal_check_{user.id}",
        eligibilityType=eligibility_type if eligibility_type else user.eligibility,
    )
    db.session.add(fraud_check)
    db.session.commit()


def has_performed_honor_statement(user: users_models.User, eligibility_type: users_models.EligibilityType) -> bool:
    fraud_checks = user.beneficiaryFraudChecks
    return any(
        fraud_check.type == models.FraudCheckType.HONOR_STATEMENT
        and fraud_check.eligibilityType == eligibility_type
        and fraud_check.status == models.FraudCheckStatus.OK
        for fraud_check in fraud_checks
    )
