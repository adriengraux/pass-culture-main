import { shallow } from 'enzyme'
import React from 'react'

import ProfileHeader from '../ProfileHeader'
import { NON_BREAKING_SPACE } from '../../../../../utils/specialCharacters'

describe('profileHeader', () => {
  let props

  beforeEach(() => {
    props = {
      currentUser: {
        publicName: 'Rosa Bonheur',
        wallet_balance: 153,
        wallet_date_created: '2018-12-23T09:07:48.914901Z',
      },
    }
  })

  it('should display my pseudo, my wallet balance and my end validity date', () => {
    // When
    const wrapper = shallow(<ProfileHeader {...props} />)

    // Then
    const pseudo = wrapper.find({ children: 'Rosa Bonheur' })
    const walletBalance = wrapper.find({ children: `153${NON_BREAKING_SPACE}€` })
    const endValidityDate = wrapper.find({ children: 'crédit valable jusqu’au 23/12/2020' })
    expect(pseudo).toHaveLength(1)
    expect(walletBalance).toHaveLength(1)
    expect(endValidityDate).toHaveLength(1)
  })
})
