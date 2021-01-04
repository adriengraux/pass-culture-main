import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

export const fieldLabels = {
  author: { label: 'Auteur', exact: false },
  bookingEmail: { label: 'Être notifié par email des réservations à :', exact: false },
  description: { label: 'Description', exact: false },
  durationMinutes: { label: 'Durée', exact: false },
  isbn: { label: 'ISBN', exact: false },
  isDuo: { label: 'Accepter les réservations "duo"', exact: false },
  isNational: { label: 'Rayonnement national', exact: true },
  name: { label: "Titre de l'offre", exact: true },
  musicSubType: { label: 'Sous genre', exact: false },
  musicType: { label: 'Genre musical', exact: false },
  offererId: { label: 'Structure', exact: true },
  performer: { label: 'Interprète', exact: false },
  receiveNotificationEmails: { label: 'Recevoir les emails de réservation', exact: true },
  showSubType: { label: 'Sous type', exact: false },
  showType: { label: 'Type de spectacle', exact: false },
  stageDirector: { label: 'Metteur en scène', exact: false },
  speaker: { label: 'Intervenant', exact: false },
  type: { label: 'Type', exact: true },
  url: { label: 'URL', exact: false },
  venueId: { label: 'Lieu', exact: true },
  visa: { label: 'Visa d’exploitation', exact: false },
  withdrawalDetails: { label: 'Informations de retrait', exact: false },
}

export const getOfferInputForField = async fieldName => {
  const { label, exact } = fieldLabels[fieldName]
  return await screen.findByLabelText(label, { exact })
}

export const getInputErrorForField = async fieldName => {
  let errorInput
  await waitFor(() => (errorInput = screen.queryByTestId(`input-error-field-${fieldName}`)))
  return errorInput
}

export const setOfferValues = async values => {
  const checkboxes = ['isDuo', 'receiveNotificationEmails']
  const selects = [
    'musicType',
    'musicSubType',
    'offererId',
    'showType',
    'showSubType',
    'type',
    'venueId',
  ]
  const setFormValueForField = async (field, value) => {
    let input
    const { label, exact } = fieldLabels[field]
    input = await screen.findByLabelText(label, { exact })
    if (checkboxes.includes(field)) {
      userEvent.click(input)
    } else if (selects.includes(field)) {
      userEvent.selectOptions(input, value)
    } else {
      userEvent.clear(input)
      userEvent.type(input, value)
    }

    return input
  }

  const modifiedInputs = {}
  for (const fieldName in values) {
    if (fieldName === 'extraData') {
      modifiedInputs[fieldName] = await setOfferValues(values.extraData)
    } else {
      modifiedInputs[fieldName] = await setFormValueForField(fieldName, values[fieldName])
    }
  }

  return Promise.resolve(modifiedInputs)
}
