import { connect } from 'react-redux'
import { requestData } from 'redux-saga-data'

import { offererNormalizer } from 'utils/normalizers'

import ApiKey from './ApiKey'

const mapDispatchToProps = dispatch => ({
  loadOffererById: offererId => {
    dispatch(
      requestData({
        apiPath: `/offerers/${offererId}`,
        normalizer: offererNormalizer,
      })
    )
  },
})

export default connect(null, mapDispatchToProps)(ApiKey)
