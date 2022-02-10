/*
 * @debt complexity "Gaël: file nested too deep in directory structure"
 * @debt directory "Gaël: this file should be migrated within the new directory structure"
 * @debt deprecated "Gaël: deprecated usage of react-final-form"
 * @debt standard "Gaël: migration from classes components to function components"
 */

import PropTypes from 'prop-types'
import React, { PureComponent } from 'react'
import { Form } from 'react-final-form'
import { getCanSubmit, parseSubmitErrors } from 'react-final-form-utils'
import { NavLink } from 'react-router-dom'

import Icon from 'components/layout/Icon'
import PageTitle from 'components/layout/PageTitle/PageTitle'
import Spinner from 'components/layout/Spinner'
import Titles from 'components/layout/Titles/Titles'

import ModifyOrCancelControl from '../controls/ModifyOrCancelControl/ModifyOrCancelControl'
import ReturnOrSubmitControl from '../controls/ReturnOrSubmitControl/ReturnOrSubmitControl'
import AccessibilityFields, {
  autoFillNoDisabilityCompliantDecorator,
} from '../fields/AccessibilityFields'
import BankInformation from '../fields/BankInformationFields'
import BusinessUnitFields from '../fields/BankInformationFields/BusinessUnitFields'
import ContactInfosFields from '../fields/ContactInfosFields'
import IdentifierFields, {
  bindGetSiretInformationToSiret,
} from '../fields/IdentifierFields'
import LocationFields, {
  bindGetSuggestionsToLatitude,
  bindGetSuggestionsToLongitude,
  FRANCE_POSITION,
} from '../fields/LocationFields'
import WithdrawalDetailsFields from '../fields/WithdrawalDetailsFields'
import { formatSiret } from '../siret/formatSiret'

class VenueCreation extends PureComponent {
  constructor() {
    super()
    this.state = {
      isReady: false,
      isRequestPending: false, // TODO when removing requestData on submit, add a isLoading state
      offerer: null,
      venueTypes: null,
      venueLabels: null,
    }
  }

  componentDidMount() {
    const { handleInitialRequest } = this.props

    handleInitialRequest().then(({ offerer, venueTypes, venueLabels }) => {
      this.setState({
        isReady: true,
        offerer,
        venueTypes,
        venueLabels,
      })
    })
  }

  handleFormFail = formResolver => (payload) => {
    const { handleSubmitRequestFail } = this.props
    const nextState = { isRequestPending: false }
    const errors = parseSubmitErrors(payload.errors)
    handleSubmitRequestFail(payload.errors)
    this.setState(nextState, () => formResolver(errors))
  }

  handleFormSuccess = formResolver => (payload) => {
    const {
      handleSubmitRequestSuccess,
      history,
      match: {
        params: { offererId },
      },
      trackCreateVenue,
    } = this.props

    const nextState = { isRequestPending: false }

    this.setState(nextState, () => {
      handleSubmitRequestSuccess(payload)
      formResolver()
    })

    const createdVenueId = action.payload.datum.id

    const next = `/accueil?structure=${offererId}`
    history.push(next)
    trackCreateVenue(createdVenueId)
  }

  handleOnFormSubmit = formValues => {
    const { handleSubmitRequest } = this.props

    return new Promise(resolve => {
      handleSubmitRequest({
        formValues,
        handleFail: this.handleFormFail(resolve),
        handleSuccess: this.handleFormSuccess(resolve),
      })
    })
  }

  onHandleRender = formProps => {
    const {
      history,
      match: {
        params: { offererId },
      },
      isBankInformationWithSiretActive,
      isEntrepriseApiDisabled,
    } = this.props
    const { isRequestPending, venueTypes, venueLabels, offerer } = this.state
    const readOnly = false

    const canSubmit = getCanSubmit(formProps)
    const { form, handleSubmit, values } = formProps
    const {
      isLocationFrozen: formIsLocationFrozen,
      latitude: formLatitude,
      longitude: formLongitude,
      siret: formSiret,
    } = values

    const siretValidOnCreation =
      formSiret && formatSiret(formSiret).length === 14
    return (
      <form name="venue" onSubmit={handleSubmit}>
        <IdentifierFields
          fieldReadOnlyBecauseFrozenFormSiret={siretValidOnCreation}
          formSiret={formSiret}
          isCreatedEntity
          isEntrepriseApiDisabled={isEntrepriseApiDisabled}
          readOnly={readOnly}
          venueLabels={venueLabels}
          venueTypes={venueTypes}
        />
        <WithdrawalDetailsFields isCreatedEntity readOnly={readOnly} />
        {isBankInformationWithSiretActive ? (
          <BusinessUnitFields isCreatingVenue offerer={offerer} />
        ) : (
          <BankInformation offerer={offerer} />
        )}
        <LocationFields
          fieldReadOnlyBecauseFrozenFormSiret={siretValidOnCreation}
          form={form}
          formIsLocationFrozen={formIsLocationFrozen}
          formLatitude={
            formLatitude === '' ? FRANCE_POSITION.latitude : formLatitude
          }
          formLongitude={
            formLongitude === '' ? FRANCE_POSITION.longitude : formLongitude
          }
          readOnly={readOnly}
        />
        <AccessibilityFields />
        <ContactInfosFields readOnly={false} />
        <hr />
        <div
          className="field is-grouped is-grouped-centered"
          style={{ justifyContent: 'space-between' }}
        >
          <ModifyOrCancelControl
            form={form}
            history={history}
            isCreatedEntity
            offererId={offererId}
            readOnly={readOnly}
          />

          <ReturnOrSubmitControl
            canSubmit={canSubmit}
            isCreatedEntity
            isRequestPending={isRequestPending}
            offererId={offererId}
            readOnly={readOnly}
          />
        </div>
      </form>
    )
  }

  render() {
    const {
      formInitialValues,
      match: {
        params: { offererId },
      },
      isEntrepriseApiDisabled,
    } = this.props
    const { isReady } = this.state

    const decorators = [
      autoFillNoDisabilityCompliantDecorator,
      bindGetSuggestionsToLatitude,
      bindGetSuggestionsToLongitude,
    ]
    if (!isEntrepriseApiDisabled) {
      decorators.push(bindGetSiretInformationToSiret)
    }

    return (
      <div className="venue-page">
        <NavLink
          className="back-button has-text-primary"
          to={`/accueil?structure=${offererId}`}
        >
          <Icon svg="ico-back" />
          Accueil
        </NavLink>
        <PageTitle title="Créer un lieu" />
        <Titles title="Lieu" />
        <p className="advice">Ajoutez un lieu où accéder à vos offres.</p>

        {!isReady && <Spinner />}

        {isReady && (
          <Form
            decorators={decorators}
            initialValues={formInitialValues}
            name="venue"
            onSubmit={this.handleOnFormSubmit}
            render={this.onHandleRender}
          />
        )}
      </div>
    )
  }
}

VenueCreation.propTypes = {
  formInitialValues: PropTypes.shape().isRequired,
  handleInitialRequest: PropTypes.func.isRequired,
  handleSubmitRequest: PropTypes.func.isRequired,
  handleSubmitRequestFail: PropTypes.func.isRequired,
  handleSubmitRequestSuccess: PropTypes.func.isRequired,
  history: PropTypes.shape().isRequired,
  isBankInformationWithSiretActive: PropTypes.bool.isRequired,
  isEntrepriseApiDisabled: PropTypes.bool.isRequired,
  match: PropTypes.shape().isRequired,
  trackCreateVenue: PropTypes.func.isRequired,
}

export default VenueCreation
