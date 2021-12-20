/*
 * @debt complexity "Gaël: the file contains eslint error(s) based on our new config"
 * @debt directory "Gaël: this file should be migrated within the new directory structure"
 */

import PropTypes from 'prop-types'
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import useActiveFeature from 'components/hooks/useActiveFeature'
import Banner from 'components/layout/Banner/Banner'
import Icon from 'components/layout/Icon'
import Select from 'components/layout/inputs/Select'

import { STEP_OFFERER_HASH } from '../HomepageBreadcrumb'

import { ReactComponent as ClosedEyeSvg } from './assets/ico-eye-close.svg'
import { ReactComponent as OpenedEyeSvg } from './assets/ico-eye-open.svg'
import BankInformations from './BankInformations'
import BusinessUnits from './BusinessUnits'

const hasRejectedOrDraftBankInformation = offerer =>
  Boolean(
    offerer.demarchesSimplifieesApplicationId && !offerer.iban && !offerer.bic
  )

const initialIsExpanded = (
  hasPhysicalVenues,
  isBankInformationWithSiretActive,
  hasInvalidBusinessUnits
) => {
  return (
    !hasPhysicalVenues ||
    (isBankInformationWithSiretActive && hasInvalidBusinessUnits)
  )
}

const OffererDetails = ({
  businessUnitList,
  handleChangeOfferer,
  hasPhysicalVenues,
  isUserOffererValidated,
  offererOptions,
  selectedOfferer,
}) => {
  const isBankInformationWithSiretActive = useActiveFeature(
    'ENFORCE_BANK_INFORMATION_WITH_SIRET'
  )

  const hasRejectedOrDraftOffererBankInformations = useMemo(() => {
    if (!selectedOfferer) return false
    return hasRejectedOrDraftBankInformation(selectedOfferer)
  }, [selectedOfferer])

  const hasInvalidBusinessUnits = useMemo(() => {
    if (!isBankInformationWithSiretActive) return false
    if (!selectedOfferer) return false
    return (
      businessUnitList.filter(businessUnit => !businessUnit.siret).length > 0
    )
  }, [selectedOfferer, businessUnitList, isBankInformationWithSiretActive])

  const [isExpanded, setIsExpanded] = useState(
    initialIsExpanded(
      hasPhysicalVenues,
      isBankInformationWithSiretActive,
      hasInvalidBusinessUnits
    )
  )

  useEffect(
    () =>
      setIsExpanded(
        initialIsExpanded(
          hasPhysicalVenues,
          isBankInformationWithSiretActive,
          hasInvalidBusinessUnits
        )
      ),
    [
      hasPhysicalVenues,
      isBankInformationWithSiretActive,
      hasInvalidBusinessUnits,
    ]
  )

  const toggleVisibility = useCallback(
    () => setIsExpanded(currentVisibility => !currentVisibility),
    []
  )

  return (
    <div className="h-card h-card-secondary" data-testid="offerrer-wrapper">
      <div className={`h-card-inner${isExpanded ? '' : ' h-no-bottom'}`}>
        <div className="od-header">
          <Select
            handleSelection={handleChangeOfferer}
            id={STEP_OFFERER_HASH}
            label=""
            name="offererId"
            options={offererOptions}
            selectedValue={selectedOfferer.id}
          />
          <div className="od-separator vertical" />
          <button
            className={`tertiary-button${isExpanded ? ' od-primary' : ''}`}
            onClick={toggleVisibility}
            type="button"
          >
            {isExpanded ? (
              <>
                <ClosedEyeSvg />
                Masquer
              </>
            ) : (
              <>
                <OpenedEyeSvg />
                Afficher
              </>
            )}
          </button>
          {isBankInformationWithSiretActive
            ? hasInvalidBusinessUnits && (
                <Icon
                  alt="SIRET Manquant"
                  className="ico-bank-warning"
                  svg="ico-alert-filled"
                />
              )
            : selectedOfferer.hasMissingBankInformation && (
                <Icon
                  alt="Informations bancaires manquantes"
                  className="ico-bank-warning"
                  svg="ico-alert-filled"
                />
              )}
          <div className="od-separator vertical small" />
          {isUserOffererValidated ? (
            <Link
              className="tertiary-link"
              to={`/structures/${selectedOfferer.id}`}
            >
              <Icon svg="ico-outer-pen" />
              Modifier
            </Link>
          ) : (
            <button className="tertiary-button" disabled type="button">
              <Icon svg="ico-outer-pen" />
              Modifier
            </button>
          )}
        </div>

        {isExpanded && (
          <>
            <div className="od-separator horizontal" />
            {!selectedOfferer.isValidated && (
              <Banner type="notification-info">
                Votre structure est en cours de validation
              </Banner>
            )}
            {isUserOffererValidated && (
              <div className="h-card-cols">
                <div className="h-card-col">
                  <h3 className="h-card-secondary-title">
                    Informations pratiques
                  </h3>
                  <div className="h-card-content">
                    <ul className="h-description-list">
                      <li className="h-dl-row">
                        <span className="h-dl-title">Siren :</span>
                        <span className="h-dl-description">
                          {selectedOfferer.siren}
                        </span>
                      </li>

                      <li className="h-dl-row">
                        <span className="h-dl-title">Désignation :</span>
                        <span className="h-dl-description">
                          {selectedOfferer.name}
                        </span>
                      </li>

                      <li className="h-dl-row">
                        <span className="h-dl-title">{'Siège social : '}</span>
                        <address className="od-address">
                          {`${selectedOfferer.address} `}
                          {selectedOfferer.hasMissingBankInformation && <br />}
                          {`${selectedOfferer.postalCode} ${selectedOfferer.city}`}
                        </address>
                      </li>
                    </ul>
                  </div>
                </div>
                {isBankInformationWithSiretActive && hasInvalidBusinessUnits ? (
                  <div className="h-card-col">
                    <BusinessUnits offererId={selectedOfferer.id} />
                  </div>
                ) : (
                  (selectedOfferer.hasMissingBankInformation ||
                    hasRejectedOrDraftOffererBankInformations) && (
                    <div className="h-card-col">
                      <BankInformations
                        hasMissingBankInformation={
                          selectedOfferer.hasMissingBankInformation
                        }
                        hasRejectedOrDraftOffererBankInformations={
                          hasRejectedOrDraftOffererBankInformations
                        }
                        offerer={selectedOfferer}
                      />
                    </div>
                  )
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

OffererDetails.propTypes = {
  businessUnitList: PropTypes.arrayOf(PropTypes.shape()).isRequired,
  handleChangeOfferer: PropTypes.func.isRequired,
  hasPhysicalVenues: PropTypes.bool.isRequired,
  isUserOffererValidated: PropTypes.bool.isRequired,
  offererOptions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      displayName: PropTypes.string.isRequired,
    })
  ).isRequired,
  selectedOfferer: PropTypes.shape().isRequired,
}

export default OffererDetails
