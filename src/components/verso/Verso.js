/* eslint
  semi: [2, "always"]
  react/jsx-one-expression-per-line: 0 */
import classnames from 'classnames';
import PropTypes from 'prop-types';
import React from 'react';

import Footer from '../layout/Footer';
import VersoInfo from './VersoInfo';
import VersoHeader from './VersoHeader';
import VersoControl from './VersoControl';
import VersoInfoTuto from './VersoInfoTuto';

class Verso extends React.PureComponent {
  render() {
    const {
      areDetailsVisible,
      backgroundColor,
      extraClassName,
      forceDetailsVisible,
      isTuto,
      mediationId,
      offerName,
      offerVenue,
    } = this.props;

    const flipped = forceDetailsVisible || areDetailsVisible;
    const showHeader = offerName && offerVenue;
    return (
      <div
        className={classnames('verso', extraClassName, {
          flipped,
        })}
      >
        <div className="verso-wrapper with-padding-top">
          {showHeader && (
            <VersoHeader
              title={offerName}
              subtitle={offerVenue}
              backgroundColor={backgroundColor}
            />
          )}
          {!isTuto && <VersoControl />}
          {!isTuto && <VersoInfo />}
          {isTuto && <VersoInfoTuto mediationId={mediationId} />}
        </div>
        <Footer id="verso-footer" borderTop colored={!isTuto} />
      </div>
    );
  }
}

Verso.defaultProps = {
  backgroundColor: null,
  extraClassName: null,
  forceDetailsVisible: false,
  mediationId: null,
  offerName: null,
  offerVenue: null,
};

Verso.propTypes = {
  areDetailsVisible: PropTypes.bool.isRequired,
  backgroundColor: PropTypes.string,
  extraClassName: PropTypes.string,
  forceDetailsVisible: PropTypes.bool,
  isTuto: PropTypes.bool.isRequired,
  mediationId: PropTypes.string,
  offerName: PropTypes.string,
  offerVenue: PropTypes.string,
};

export default Verso;
