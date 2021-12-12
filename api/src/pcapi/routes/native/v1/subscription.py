import logging
from typing import Optional

from pcapi.core.fraud import api as fraud_api
from pcapi.core.subscription import api as subscription_api
from pcapi.core.subscription import school_types
from pcapi.core.users import models as users_models
from pcapi.routes.native.security import authenticated_user_required
from pcapi.serialization.decorator import spectree_serialize

from . import blueprint
from .serialization import subscription as serializers


logger = logging.getLogger(__name__)


@blueprint.native_v1.route("/subscription/next_step", methods=["GET"])
@spectree_serialize(
    response_model=serializers.NextSubscriptionStepResponse,
    on_success_status=200,
    api=blueprint.api,
)  # type: ignore
@authenticated_user_required
def next_subscription_step(
    user: users_models.User,
) -> Optional[serializers.NextSubscriptionStepResponse]:
    return serializers.NextSubscriptionStepResponse(
        next_subscription_step=subscription_api.get_next_subscription_step(user),
        allowed_identity_check_methods=subscription_api.get_allowed_identity_check_methods(user),
        maintenance_page_type=subscription_api.get_maintenance_page_type(user),
    )


@blueprint.native_v1.route("/subscription/profile", methods=["POST"])
@spectree_serialize(on_success_status=204, api=blueprint.api)
@authenticated_user_required
def update_profile(user: users_models.User, body: serializers.ProfileUpdateRequest) -> None:
    # TODO: Corentin: remove this when we send ids in the request body
    if body.activity_id is not None:
        activity = users_models.ActivityEnum[body.activity_id.value].value
    else:
        activity = body.activity.value

    subscription_api.update_user_profile(
        user,
        first_name=body.first_name,
        last_name=body.last_name,
        address=body.address,
        city=body.city,
        postal_code=body.postal_code,
        activity=activity,
        school_type=users_models.SchoolTypeEnum[body.school_type_id.value] if body.school_type_id is not None else None,
    )


@blueprint.native_v1.route("/subscription/school_types", methods=["GET"])
@spectree_serialize(
    response_model=serializers.SchoolTypesResponse,
    on_success_status=200,
    api=blueprint.api,
)  # type: ignore
def get_school_types() -> serializers.SchoolTypesResponse:
    return serializers.SchoolTypesResponse(
        school_types=[
            serializers.SchoolTypeResponseModel.from_orm(school_type) for school_type in school_types.ALL_SCHOOL_TYPES
        ],
        activities=[serializers.ActivityResponseModel.from_orm(activity) for activity in school_types.ALL_ACTIVITIES],
    )


@blueprint.native_v1.route("/subscription/honor_statement", methods=["POST"])
@spectree_serialize(on_success_status=204, api=blueprint.api)
@authenticated_user_required
def create_honor_statement_fraud_check(user: users_models.User) -> None:
    fraud_api.create_honor_statement_fraud_check(user, "statement from /subscription/honor_statement endpoint")

    if subscription_api.can_activate_beneficiary(user, user.eligibility):
        subscription_api.activate_beneficiary(user)
