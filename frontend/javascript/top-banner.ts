import { slideUp } from 'froide/frontend/javascript/lib/misc'

interface IDonationBannerStore {
  timestamp: number
}

function showTopBanner(): void {
  const topBanner = document.querySelector<HTMLElement>('.top-banner')
  if (topBanner === null) return

  const hasAnimation =
    topBanner.firstElementChild?.hasAttribute('data-slide') === true

  const removeBanner = (): void => topBanner.remove()

  const itemName = 'top-banner'
  const now = new Date().getTime()
  const data = localStorage.getItem(itemName)

  if (data !== null) {
    const last = JSON.parse(data) as IDonationBannerStore
    if (last.timestamp !== 0 && now - last.timestamp < 60 * 60 * 24 * 1000) {
      return removeBanner()
    }
  }
  localStorage.removeItem(itemName)

  const hideBanner = (el: HTMLElement, e: Event): void => {
    e.preventDefault()

    const data = JSON.stringify({ timestamp: now })
    localStorage.setItem(itemName, data)

    if (hasAnimation) {
      slideUp(el)
      el.addEventListener('transitionend', removeBanner)
      setTimeout(removeBanner, 1000)
    } else {
      removeBanner()
    }

    window._paq?.push(['trackEvent', 'ads', 'topBanner', 'close'])
  }

  // various checks, if banner should not be shown on current page
  const path = document.location.pathname
  const blockedPaths = [
    '/spenden/',
    '/donate/',
    '/gesendet/',
    '/sent/',
    '/payment/',
    '/abgeschlossen/',
    '/anfrage-stellen/',
    '/make-request/',
    '/account/'
  ]
  if (blockedPaths.some((p) => path.includes(p))) {
    return removeBanner()
  }

  const linksInBanner = topBanner.querySelectorAll('a')
  for (const link of linksInBanner) {
    if (path.startsWith(link.pathname)) {
      return removeBanner()
    }
  }

  const donationForm = document.querySelector('.donation-form')
  if (donationForm !== null) {
    return removeBanner()
  }

  const noBanner = document.querySelector('[data-nobanner]')
  if (noBanner !== null) {
    return removeBanner()
  }

  if (window.localStorage === undefined) {
    return removeBanner()
  }

  // close buttons
  const closeButtons = topBanner.querySelectorAll('.banner-close')
  closeButtons.forEach((closeButton) => {
    closeButton.addEventListener('click', (e) => hideBanner(topBanner, e))
  })

  // show banner
  topBanner.style.display = 'block'

  // tracking
  setTimeout(() => {
    window._paq?.push(['trackEvent', 'ads', 'topBanner', 'shown'])
  }, 3000)
}

document.addEventListener('DOMContentLoaded', showTopBanner)
