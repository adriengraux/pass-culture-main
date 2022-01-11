import datetime
import logging
from typing import Callable

import flask
import flask_admin
import flask_admin.helpers
import flask_admin.model.helpers
import flask_login
from flask_sqlalchemy import BaseQuery
from markupsafe import Markup
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.sql import ColumnElement
from werkzeug import Response
import wtforms.validators

from pcapi.admin import base_configuration
import pcapi.core.fraud.api as fraud_api
import pcapi.core.fraud.models as fraud_models
from pcapi.core.mails.transactional.users.subscription_document_error import send_subscription_document_error_email
from pcapi.core.subscription import messages as subscription_messages
import pcapi.core.subscription.api as subscription_api
import pcapi.core.subscription.exceptions as subscription_exceptions
import pcapi.core.users.api as users_api
import pcapi.core.users.models as users_models
from pcapi.models import db
from pcapi.models.beneficiary_import import BeneficiaryImportSources
from pcapi.models.beneficiary_import_status import ImportStatus
from pcapi.models.feature import FeatureToggle


logger = logging.getLogger(__name__)


def beneficiary_fraud_results_formatter(view, context, model, name) -> Markup:
    css_classes = {
        fraud_models.FraudStatus.OK: "badge-success",
        fraud_models.FraudStatus.KO: "badge-danger",
        fraud_models.FraudStatus.SUSPICIOUS: "badge-warning",
        fraud_models.FraudStatus.SUBSCRIPTION_ON_HOLD: "badge-warning",
    }
    if not model.beneficiaryFraudResults:
        return Markup("""<span class="badge badge-secondary">Inconnu</span>""")

    statuses = Markup("<div>")
    for (index, fraud_result) in enumerate(model.beneficiaryFraudResults):
        statuses += Markup("""<span class="badge {css_class}" style="{extra_style}">{value}</span>""").format(
            css_class=css_classes[fraud_result.status],
            extra_style="margin-left: 8px" if index > 0 else "",
            value=fraud_result.status.value,
        )
    statuses += Markup("</div>")
    return statuses


def beneficiary_fraud_review_formatter(view, context, model, name) -> Markup:
    result_mapping_class = {
        fraud_models.FraudReviewStatus.OK: "badge-success",
        fraud_models.FraudReviewStatus.KO: "badge-danger",
        fraud_models.FraudReviewStatus.REDIRECTED_TO_DMS: "badge-secondary",
    }
    if model.beneficiaryFraudReview is None:
        return Markup("""<span class="badge badge-secondary">inconnu</span>""")

    reviewer = model.beneficiaryFraudReview.author
    reviewer_name = f"{reviewer.firstName} {reviewer.lastName}"
    review_result = model.beneficiaryFraudReview.review
    badge = result_mapping_class[review_result]
    return Markup(
        """
          <div><span>{reviewer_name}</span></div>
          <span class="badge {badge}">{review_result_value}</span>
        """
    ).format(reviewer_name=reviewer_name, badge=badge, review_result_value=review_result.value)


def beneficiary_fraud_checks_formatter(view, context, model, name) -> Markup:
    html = Markup("<ul>")
    for instance in model.beneficiaryFraudChecks:
        html += Markup("<li>{instance.type.value}</li>").format(instance=instance)
    html += Markup("</ul>")
    return html


class FraudReviewForm(wtforms.Form):
    class Meta:
        locales = ["fr"]

    reason = wtforms.TextAreaField(validators=[wtforms.validators.DataRequired()])
    review = wtforms.SelectField(
        choices=[(item.name, item.value) for item in fraud_models.FraudReviewStatus],
        validators=[wtforms.validators.DataRequired()],
    )


class IDPieceNumberForm(wtforms.Form):
    class Meta:
        locales = ["fr"]

    id_piece_number = wtforms.StringField(
        validators=[wtforms.validators.DataRequired(), wtforms.validators.Length(min=8, max=12)]
    )


class BeneficiaryView(base_configuration.BaseAdminView):
    VIEW_FILTERS = {
        "INTERNAL": sqlalchemy.and_(
            users_models.User.has_admin_role.is_(False),
            users_models.User.has_pro_role.is_(False),
        ),
        "UNFILTERED": False,
    }

    column_list = [
        "id",
        "firstName",
        "lastName",
        "email",
        "beneficiaryFraudResults",
        "beneficiaryFraudChecks",
        "beneficiaryFraudReview",
        "dateCreated",
    ]
    column_labels = {
        "firstName": "Prénom",
        "lastName": "Nom",
        "beneficiaryFraudResults": "Statut(s)",
        "beneficiaryFraudChecks": "Vérifications anti fraudes",
        "beneficiaryFraudReview": "Evaluation Manuelle",
        "dateCreated": "Date de creation de compte",
    }

    column_searchable_list = ["id", "email", "firstName", "lastName"]
    column_filters = [
        "email",
        "dateCreated",
        "beneficiaryFraudResults.status",
        "beneficiaryFraudChecks.type",
        "beneficiaryFraudReview",
    ]

    column_sortable_list = [
        "dateCreated",
    ]

    can_view_details = True
    details_template = "admin/support_beneficiary_details.html"
    list_template = "admin/support_beneficiary_list.html"

    page_size = 100

    @property
    def column_type_formatters(self) -> dict[type, Callable]:
        type_formatters = super().column_type_formatters
        type_formatters[datetime.datetime] = lambda view, value: value.strftime("%d/%m/%Y à %H:%M:%S")
        return type_formatters

    @property
    def column_formatters(self) -> dict[str, Callable]:
        formatters = super().column_formatters
        formatters.update(
            {
                "beneficiaryFraudChecks": beneficiary_fraud_checks_formatter,
                "beneficiaryFraudResults": beneficiary_fraud_results_formatter,
                "beneficiaryFraudReview": beneficiary_fraud_review_formatter,
            }
        )
        return formatters

    def _are_search_and_filters_empty(self) -> bool:
        view_args = self._get_list_extra_args()
        return (not view_args.search) and (not view_args.filters)

    def get_view_filter(self) -> ColumnElement:
        role = "INTERNAL"
        if self._are_search_and_filters_empty():
            role = "UNFILTERED"
        return self.VIEW_FILTERS[role]

    def get_query(self) -> BaseQuery:
        view_filter = self.get_view_filter()
        query = users_models.User.query.filter(view_filter).options(
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudChecks),
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudResults),
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudReview),
        )
        return query

    def get_count_query(self) -> BaseQuery:
        view_filter = self.get_view_filter()
        return users_models.User.query.filter(view_filter).with_entities(sqlalchemy.func.count(users_models.User.id))

    @flask_admin.expose("/details/")
    def details_view(self) -> Response:
        return_url = flask_admin.helpers.get_redirect_target() or self.get_url(".index_view")

        if not self.can_view_details:
            return flask.redirect(return_url)

        object_id = flask_admin.model.helpers.get_mdict_item_or_list(flask.request.args, "id")
        if object_id is None:
            return flask.redirect(return_url)

        user = self.get_one(object_id)

        if user is None:
            flask.flash(flask_admin.babel.gettext("Record does not exist."), "error")
            return flask.redirect(return_url)

        if self.details_modal and flask.request.args.get("modal"):
            template = self.details_modal_template
        else:
            template = self.details_template

        return self.render(
            template,
            model=user,
            details_columns=self._details_columns,
            get_value=self.get_detail_value,
            return_url=return_url,
            has_performed_identity_check=fraud_api.has_user_performed_identity_check(user),
            enum_update_request_value=users_models.EmailHistoryEventTypeEnum.UPDATE_REQUEST.value,
            subscription_items=_get_subscription_items_by_eligibility(user),
            next_subscription_step=subscription_api.get_next_subscription_step(user),
        )

    @flask_admin.expose(
        "/validate/beneficiary/<user_id>", methods=["POST"]
    )  # pylint: disable=too-many-return-statements
    def validate_beneficiary(self, user_id: int) -> Response:
        if not FeatureToggle.BENEFICIARY_VALIDATION_AFTER_FRAUD_CHECKS.is_active():
            flask.flash("Fonctionnalité non activée", "error")
            return flask.redirect(flask.url_for(".details_view", id=user_id))
        if not self.check_super_admins():
            flask.flash("Vous n'avez pas les droits suffisants pour activer ce bénéficiaire", "error")
            return flask.redirect(flask.url_for(".details_view", id=user_id))
        form = FraudReviewForm(flask.request.form)
        if not form.validate():
            errors_html = Markup("Erreurs lors de la validation du formulaire: <br>")
            for field, error in form.errors.items():
                errors_html += Markup("{field}: {error[0]}").format(field=field, error=error)
            flask.flash(errors_html, "error")
            return flask.redirect(flask.url_for(".details_view", id=user_id))
        user = users_models.User.query.get(user_id)
        if not user:
            flask.flash("Cet utilisateur n'existe pas", "error")
            return flask.redirect(flask.url_for(".index_view"))

        if user.beneficiaryFraudReview:
            flask.flash(
                f"Une revue manuelle a déjà été réalisée sur l'utilisateur {user.id} {user.firstName} {user.lastName}"
            )
            return flask.redirect(flask.url_for(".details_view", id=user_id))

        review = fraud_models.BeneficiaryFraudReview(
            user=user, author=flask_login.current_user, reason=form.data["reason"], review=form.data["review"]
        )
        if review.review == fraud_models.FraudReviewStatus.OK.value:
            users_api.update_user_information_from_external_source(user, fraud_api.get_source_data(user))
            eligibility = fraud_api.get_eligibility_type(fraud_api.get_source_data(user))

            if eligibility is None:
                flask.flash("La date de naissance du dossier indique que l'utilisateur n'est pas éligible", "error")
                return flask.redirect(flask.url_for(".details_view", id=user_id))

            try:
                beneficiary_import = subscription_api.BeneficiaryImport(
                    sourceId=None,
                    source=BeneficiaryImportSources.jouve.value,
                    beneficiary=user,
                    eligibilityType=fraud_api.get_eligibility_type(fraud_api.get_source_data(user)),
                )
                beneficiary_import.setStatus(ImportStatus.CREATED.value)

                subscription_api.activate_beneficiary(user, "fraud_validation")
            except subscription_exceptions.CannotUpgradeBeneficiaryRole:
                flask.flash("L'utilisateur est déjà bénéficiaire", "error")
            flask.flash(f"L'utilisateur à été activé comme bénéficiaire {user.firstName} {user.lastName}")

        elif review.review == fraud_models.FraudReviewStatus.REDIRECTED_TO_DMS.value:
            review.reason += " ; Redirigé vers DMS"
            send_subscription_document_error_email(user.email, "unread-document")
            flask.flash(f"L'utilisateur {user.firstName} {user.lastName} à été redirigé vers DMS")
            subscription_messages.on_redirect_to_dms_from_idcheck(user)
        elif review.review == fraud_models.FraudReviewStatus.KO.value:
            subscription_messages.on_fraud_review_ko(user)
        db.session.add(review)
        db.session.commit()

        flask.flash(f"Une revue manuelle ajoutée pour le bénéficiaire {user.firstName} {user.lastName}")
        return flask.redirect(flask.url_for(".details_view", id=user_id))

    @flask_admin.expose("/validate/beneficiary/phone_number/<user_id>", methods=["POST"])
    def validate_phone_number(self, user_id: int) -> Response:
        if not flask_login.current_user.has_admin_role:
            flask.flash(
                "Vous n'avez pas les droits suffisants pour valider le numéro de téléphone de cet utilisateur", "error"
            )
            return flask.redirect(flask.url_for(".details_view", id=user_id))

        user = users_models.User.query.get(user_id)
        if not user:
            flask.flash("Cet utilisateur n'existe pas", "error")
            return flask.redirect(flask.url_for(".index_view"))

        user.phoneValidationStatus = users_models.PhoneValidationStatusType.VALIDATED
        db.session.add(user)
        db.session.commit()
        logger.info("flask-admin: Manual phone validation", extra={"validated_user": user.id})
        flask.flash(f"Le n° de téléphone de l'utilisateur {user.id} {user.firstName} {user.lastName} est validé")
        return flask.redirect(flask.url_for(".details_view", id=user_id))


def _get_subscription_items_by_eligibility(user: users_models.User):
    subscription_items = []
    for method in [
        subscription_api.get_email_validation_subscription_item,
        subscription_api.get_phone_validation_subscription_item,
        subscription_api.get_user_profiling_subscription_item,
        subscription_api.get_profile_completion_subscription_item,
        subscription_api.get_identity_check_subscription_item,
        subscription_api.get_honor_statement_subscription_item,
    ]:
        subscription_items.append(
            {
                users_models.EligibilityType.UNDERAGE.name: method(user, users_models.EligibilityType.UNDERAGE),
                users_models.EligibilityType.AGE18.name: method(user, users_models.EligibilityType.AGE18),
            },
        )

    return subscription_items
