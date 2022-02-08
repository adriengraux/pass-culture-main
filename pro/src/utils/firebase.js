import { getAnalytics } from 'firebase/analytics'
import { logEvent as analyticsLogEvent } from 'firebase/analytics'
import { initializeApp } from 'firebase/app'

const CLICk_CREATE_ACOUNT = 'clickCreateAccount'

const firebaseConfig = {
  apiKey: process.env.FIRBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID,
  measurementId: process.env.FIREBASE_MEASUREMENT_ID,
}

const app = initializeApp(firebaseConfig)
const analyticsProvider = getAnalytics(app)

const logEvent = (event, params = {}) => {
  analyticsLogEvent(analyticsProvider, event, params)
}

export const analytics = {
  logClickCreateAccount: () => logEvent(CLICk_CREATE_ACOUNT),
}
