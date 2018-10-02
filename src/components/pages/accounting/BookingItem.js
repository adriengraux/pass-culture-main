import get from 'lodash.get'
import moment from 'moment'
import { closeModal, Icon, requestData, showModal } from 'pass-culture-shared'
import PropTypes from 'prop-types'
import React, { Component, Fragment } from 'react'
import { connect } from 'react-redux'

import eventSelector from '../../../selectors/event'
import thingSelector from '../../../selectors/thing'
import offerSelector from '../../../selectors/offer'
import offererSelector from '../../../selectors/offerer'
import selectEventOccurrenceById from '../../../selectors/selectEventOccurenceById'
import selectStockById from '../../../selectors/selectStockById'
import venueSelector from '../../../selectors/venue'
import { bookingNormalizer } from '../../../utils/normalizers'

const getBookingState = booking => {
  const { isCancelled, isUsed } = booking

  // TODO
  // if (isError) {
  //  return {
  //    picto: 'picto-warning',
  //    message: 'Erreur',
  //    text: '?'
  //  }
  //}

  if (isCancelled === true) {
    return {
      picto: 'picto-warning',
      message: 'Annulé',
    }
  }

  if (isUsed) {
    // TODO
    // if (isPayed) {
    //  return {
    //    picto: 'picto-validation',
    //    message: 'Réglé',
    //  }
    // }

    return {
      picto: 'picto-encours-S',
      message: 'Validé',
    }
  }

  return {
    picto: 'picto-temps-S',
    message: 'En attente',
  }
}

class BookingItem extends Component {
  onCancelClick = () => {
    const { booking, dispatch, isCancelled } = this.props
    const { id } = booking
    console.log('cancel booking for id:', id)

    if (isCancelled) {
      console.warn(`Weird your booking ${id} is already cancelled`)
      return
    }

    dispatch(
      showModal(
        <div>
          Êtes-vous surs de vouloir annuler cette réservation ?
          <div className="level">
            <button
              className="button is-primary level-item"
              onClick={() => {
                dispatch(
                  requestData('PATCH', `bookings/${id}`, {
                    body: {
                      isCancelled: true,
                    },
                    normalizer: bookingNormalizer,
                  })
                )
                dispatch(closeModal())
              }}>
              Oui
            </button>
            <button
              className="button is-primary level-item"
              onClick={() => dispatch(closeModal())}>
              Non
            </button>
          </div>
        </div>,
        { isUnclosable: true }
      )
    )
  }

  render() {
    const { booking, event, offerer, stock, thing, venue } = this.props
    const {
      amount,
      dateModified,
      id,
      isCancelled,
      isUsed,
      reimbursed_amount,
      token,
      userId,
    } = booking
    const { bookingLimitDatetime, groupSize } = stock || {}

    // TODO: we need to continue to extract the
    // view attributes from the data
    const eventOrThing = event || thing
    const { name, type } = eventOrThing || {}
    const offererName = get(offerer, 'name')
    const venueName = get(venue, 'name')
    const bookingState = getBookingState(booking)
    const { picto, message } = bookingState || {}

    return (
      <Fragment>
        <tr className="offer-item">
          <td colSpan="5" className="title">
            {name}
          </td>
          <td colSpan="5" className="title userName">
            UserId: {userId} - BookingId: {id} - Token: {token}
          </td>
          <td rowSpan="2">
            {!isCancelled && (
              <div className="navbar-item has-dropdown is-hoverable AccountingPage-actions">
                <div className="actionButton" />
                <div className="navbar-dropdown is-right">
                  <a
                    className="navbar-item cancel"
                    onClick={this.onCancelClick}>
                    <Icon svg="ico-close-r" /> Annuler la réservation
                  </a>
                </div>
              </div>
            )}
          </td>
        </tr>
        <tr className="offer-item first-col">
          <td>{moment(dateModified).format('D/MM/YY')}</td>
          <td>{type}</td>
          <td>{offererName}</td>
          <td>{venueName}</td>
          <td>
            {groupSize === 1 && <Icon svg="picto-user" />}
            {groupSize > 1 && (
              <Fragment>
                <Icon svg="picto-group" /> {groupSize}
              </Fragment>
            )}
          </td>
          <td>{moment(bookingLimitDatetime).format('D/MM/YY')}</td>
          <td>5/10</td>
          <td>{amount}</td>
          <td>{reimbursed_amount}</td>
          <td>
            <Icon svg={picto} className="picto tiny" /> {message}
          </td>
        </tr>
      </Fragment>
    )
  }
}

BookingItem.propTypes = {
  booking: PropTypes.object.isRequired,
}

export default connect((state, ownProps) => {
  const stock = selectStockById(state, ownProps.booking.stockId)
  const eventOccurrence = selectEventOccurrenceById(
    state,
    get(stock, 'eventOccurrenceId')
  )
  const offer = offerSelector(
    state,
    get(stock, 'offerId') || get(eventOccurrence, 'offerId')
  )
  const event = eventSelector(state, get(offer, 'eventId'))
  const thing = thingSelector(state, get(offer, 'thingId'))
  const venue = venueSelector(state, get(offer, 'venueId'))
  const offerer = offererSelector(state, get(venue, 'managingOffererId'))
  return {
    event,
    eventOccurrence,
    offer,
    offerer,
    stock,
    thing,
    venue,
  }
})(BookingItem)
