import cn from 'classnames'
import React, { FunctionComponent } from 'react'

import style from './VenueImagePreview.module.scss'
import { VenuePreviews } from './VenuePreviews/VenuePreviews'

interface Props {
  preview: string
  onGoToPrevious: () => void
  onUploadImage: () => void
  children?: never
}

export const VenueImagePreview: FunctionComponent<Props> = ({
  preview,
  onGoToPrevious,
  onUploadImage,
}) => (
  <div className={style['container']}>
    <header>
      <h1 className={style['header']}>Image du lieu</h1>
    </header>
    <div className={style['subtitle']}>
      Prévisualisation de votre image dans l’application pass Culture
    </div>
    <VenuePreviews preview={preview} />
    <div className={style['actions']}>
      <button
        className={cn('secondary-button', style['button'])}
        onClick={onGoToPrevious}
        title="Retour"
        type="button"
      >
        Retour
      </button>
      <button
        className={cn('primary-button', style['button'])}
        onClick={onUploadImage}
        title="Suivant"
        type="button"
      >
        Enregistrer
      </button>
    </div>
  </div>
)
