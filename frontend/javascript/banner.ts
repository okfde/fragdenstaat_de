import { slideUp } from 'froide/frontend/javascript/lib/misc'

interface DonationBannerStore {
  timestamp: number
}

function initializeBanner(banner: HTMLElement): boolean {
  const bannerId = banner.dataset.banner ?? 'unknown'

  const slide = banner.firstElementChild?.getAttribute('data-slide')

  const removeBanner = (): boolean => {
    banner.remove()
    return false
  }

  const itemName = `banner-${bannerId}`
  const now = new Date().getTime()
  const data = localStorage.getItem(itemName)

  if (data !== null) {
    const last = JSON.parse(data) as DonationBannerStore
    if (last.timestamp !== 0 && now - last.timestamp < 60 * 60 * 24 * 1000) {
      return removeBanner()
    }
  }
  localStorage.removeItem(itemName)

  const hideBanner = async (el: HTMLElement, e: Event) => {
    e.preventDefault()

    const data = JSON.stringify({ timestamp: now })
    localStorage.setItem(itemName, data)

    if (slide === 'up') {
      await slideUp(el)

      el.addEventListener('transitionend', removeBanner)
      setTimeout(removeBanner, 1000)
    } else if (slide === 'down') {
      el.style.transition = 'transform 0.3s ease-out'
      el.style.transform = 'translateY(105%)'

      el.addEventListener('transitionend', removeBanner)
      setTimeout(removeBanner, 1000)
    } else {
      removeBanner()
    }

    window._paq.push(['trackEvent', 'ads', 'topBanner', 'close'])
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
    '/account/',
    '/links/'
  ]
  if (blockedPaths.some((p) => path.includes(p))) {
    return removeBanner()
  }

  const linksInBanner = banner.querySelectorAll('a')
  for (const link of linksInBanner) {
    if (
      path.startsWith(link.pathname) &&
      link.hostname === window.location.hostname
    ) {
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

  // close buttons
  const closeButtons = banner.querySelectorAll('.banner-close')
  closeButtons.forEach((closeButton) => {
    closeButton.addEventListener('click', (e) => {
      hideBanner(banner, e)
    })
  })

  // show banner
  banner.hidden = false

  // tracking
  setTimeout(() => {
    window._paq.push(['trackEvent', 'ads', 'topBanner', 'shown'])
  }, 3000)
  return true
}

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll<HTMLElement>('.fds-banner')
    .forEach(initializeBanner)
})
