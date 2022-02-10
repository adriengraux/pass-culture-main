/*
 * @debt complexity "Gaël: the file contains eslint error(s) based on our new config"
 * @debt complexity "Gaël: file nested too deep in directory structure"
 * @debt deprecated "Gaël: deprecated usage of redux-saga-data"
 * @debt standard "Gaël: prefer useSelector hook vs connect for redux (https://react-redux.js.org/api/hooks)"
 * @debt deprecated "Gaël: deprecated usage of withQueryRouter"
 */

import { connect } from 'react-redux'
import { compose } from 'redux'

import { withQueryRouter } from 'components/hocs/with-query-router/withQueryRouter'
import withTracking from 'components/hocs/withTracking'
import * as pcapi from 'repository/pcapi/pcapi'
import { isFeatureActive } from 'store/features/selectors'
import { showNotification } from 'store/reducers/notificationReducer'
import { selectOffererById } from 'store/selectors/data/offerersSelectors'
import { selectCurrentUser } from 'store/selectors/data/usersSelectors'
import { venueNormalizer } from 'utils/normalizers'

import NotificationMessage from '../Notification'
import { formatVenuePayload } from '../utils/formatVenuePayload'
import VenueLabel from '../ValueObjects/VenueLabel'
import VenueType from '../ValueObjects/VenueType'

import VenueCreation from './VenueCreation'

export const mapStateToProps = (state, ownProps) => {
  const {
    match: {
      params: { offererId },
    },
  } = ownProps

  const currentUser = selectCurrentUser(state)
  return {
    currentUser: currentUser,
    formInitialValues: {
      managingOffererId: offererId,
      bookingEmail: currentUser.email,
    },
    offerer: selectOffererById(state, offererId),
    isBankInformationWithSiretActive: isFeatureActive(
      state,
      'ENFORCE_BANK_INFORMATION_WITH_SIRET'
    ),
    isEntrepriseApiDisabled: isFeatureActive(state, 'DISABLE_ENTERPRISE_API'),
  }
}

export const mapDispatchToProps = (dispatch, ownProps) => {
  const {
    match: {
      params: { offererId },
    },
  } = ownProps

  return {
    handleInitialRequest: async () => {
      const offererRequest = pcapi.getOfferer(offererId)
      const venueTypesRequest = pcapi.getVenueTypes().then(venueTypes => {
        return venueTypes.map(type => new VenueType(type))
      })
      const venueLabelsRequest = pcapi.getVenueLabels().then(labels => {
        return labels.map(label => new VenueLabel(label))
      })
      const [offerer, venueTypes, venueLabels] = await Promise.all([
        offererRequest,
        venueTypesRequest,
        venueLabelsRequest,
      ])

      return {
        offerer,
        venueTypes,
        venueLabels,
      }
    },

    handleSubmitRequest: async ({ formValues, handleFail, handleSuccess }) => {
      const apiPath = '/venues/'

      const body = formatVenuePayload(formValues, true)
      try {
        response = await pcapi.createVenue(body)
        handleSuccess(response)
      } catch (e) {
        // server error, response have a "ok" value set to false
        // TODO handle errors
        handleFail(response)
      }
    },

    handleSubmitRequestFail: (errors) => {
      let text = 'Une ou plusieurs erreurs sont présentes dans le formulaire.'
      if (errors.global) {
        text = `${text} ${errors.global[0]}`
      }

      dispatch(
        showNotification({
          text,
          type: 'error',
        })
      )
    },

    handleSubmitRequestSuccess: (payload) => {
      const informationsDisplayed = {
        venueId: payload.id,
        offererId,
      }

      dispatch(
        showNotification({
          text: NotificationMessage(informationsDisplayed),
          type: 'success',
        })
      )
    },
  }
}

export const mergeProps = (stateProps, dispatchProps, ownProps) => {
  return {
    ...stateProps,
    ...dispatchProps,
    ...ownProps,
    trackCreateVenue: createdVenueId => {
      ownProps.tracking.trackEvent({
        action: 'createVenue',
        name: createdVenueId,
      })
    },
  }
}

export default compose(
  withTracking('Venue'),
  withQueryRouter(),
  connect(mapStateToProps, mapDispatchToProps, mergeProps)
)(VenueCreation)
