import React, { Component } from 'react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'
import { compose } from 'redux'

import { requestData } from '../reducers/data'

const withLogin = (config = {}) => WrappedComponent => {
  const { isRequired,
    redirectTo,
    requestUserTimeout
  } = config
  const pushSigninTimeout = config.pushSigninTimeout || 500

  class _withLogin extends Component {
    constructor () {
      super()
      this.hasBackendRequest = false
      this.state = { hasConfirmRequest: false }
    }

    componentWillMount = () => {
      const { history: { push },
        user,
        requestData
      } = this.props
      if (!user) {
        this.requestUserTimeout = setTimeout(
          () => requestData('GET',
            `users/me`,
            { key: 'users', local: true }
          ), requestUserTimeout)
      } else if (redirectTo) {
        push(redirectTo)
      }
    }

    componentWillReceiveProps = nextProps => {
      const { history: { push },
        isModalActive,
        requestData
      } = this.props
      if (nextProps.user && nextProps.user !== this.props.user) {
        // BUT ACTUALLY IT IS A SUCCESS FROM THE LOCAL USER
        // NOW BETTER IS TO ALSO TO DO A QUICK CHECK
        // ON THE BACKEND TO CONFIRM THAT IT IS STILL
        // A STORED USER
        if (!this.props.user && !this.hasBackendRequest) {
          requestData('GET', `users/me`, { key: 'users' })
          this.hasBackendRequest = true
          if (redirectTo) {
            push(redirectTo)
          }
        }
      } else if (isRequired) {
        if (nextProps.user === false && this.props.user === null) {
          // CASE WHERE WE TRIED TO GET THE USER IN THE LOCAL
          // BUT WE GOT A FALSE RETURN SO WE NEED TO ASK THE BACKEND
          requestData('GET', 'users/me', { key: 'users' })
          this.hasBackendRequest = true
        } else if (!isModalActive) {
          if (nextProps.user === null && this.props.user === false) {
            // CASE WHERE WE STILL HAVE A USER NULL
            // SO WE FORCE THE SIGNIN PUSH
            push('/connexion')
          } else if (nextProps.user === false && this.props.user) {
            // CASE WE JUST SIGNOUT AND AS IS REQUIRED IS TRUE
            // WE NEED TO PROPOSE A NEW SIGNIN MODAL
            // BUT WE ARE GOING TO WAIT JUST A LITTLE BIT
            // TO MAKE A SLOW TRANSITION
            this.pushSigninTimeout = setTimeout(() =>
              push('/connexion'), pushSigninTimeout)
          }
        }
      }
    }

    componentWillUnmount () {
      this.requestUserTimeout && clearTimeout(this.requestUserTimeout)
      this.pushSigninTimeout && clearTimeout(this.pushSigninTimeout)
    }

    render () {
      return <WrappedComponent {...this.props} />
    }

  }
  return compose(
    withRouter,
    connect(
      state => ({ isModalActive: state.modal.isActive, user: state.user }),
      { requestData }
    )
  )(_withLogin)
}

export default withLogin
