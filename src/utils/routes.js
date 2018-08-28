import React from 'react'
import { Redirect } from 'react-router-dom'

import BetaPage from '../components/pages/BetaPage'
import BookingsPage from '../components/pages/BookingsPage'
import DiscoveryPage from '../components/pages/DiscoveryPage'
import FavoritesPage from '../components/pages/FavoritesPage'
import ProfilePage from '../components/pages/ProfilePage'
import SearchPage from '../components/pages/SearchPage'
import SigninPage from '../components/pages/SigninPage'
import SignupPage from '../components/pages/SignupPage'
import TermsPage from '../components/pages/TermsPage'

const routes = [
  {
    path: '/',
    render: () => <Redirect to="/beta" />,
  },
  {
    component: BetaPage,
    path: '/beta',
    title: "Bienvenue dans l'avant-première du Pass Culture",
  },
  {
    component: SigninPage,
    path: '/connexion',
    title: 'Connexion',
  },
  {
    component: SignupPage,
    path: '/inscription',
    title: 'Inscription',
  },
  /* ---------------------------------------------------
   *
   * MENU ITEMS
   * NOTE les elements ci-dessous sont les elements du main menu
   *
   ---------------------------------------------------  */
  {
    component: DiscoveryPage,
    disabled: false,
    icon: 'offres-w',
    // exemple d'URL optimale qui peut être partagée
    // par les sous composants
    path: '/decouverte/:offerId?/:mediationId?/:view(booking|verso)?',
    title: 'Les offres',
  },
  {
    component: BookingsPage,
    disabled: false,
    icon: 'calendar-w',
    path: '/reservations',
    title: 'Mes Réservations',
  },
  {
    component: FavoritesPage,
    disabled: false,
    icon: 'like-w',
    path: '/favoris',
    title: 'Mes Préférés',
  },
  {
    component: ProfilePage,
    disabled: false,
    icon: 'user-w',
    path: '/profil',
    title: 'Mon Profil',
  },
  {
    disabled: false,
    href: 'mailto:pass@culture.gouv.fr',
    icon: 'mail-w',
    title: 'Nous contacter',
  },
{
    component: SearchPage,
    path: '/recherche',
    title: 'Recherche',
  },
  {
    component: BookingsPage,
    path: '/reservations',
    title: 'Réservations',
  },
  {
    component: TermsPage,
    disabled: false,
    icon: 'txt-w',
    path: '/mentions-legales',
    title: 'Mentions Légales',
  },
]

export default routes
