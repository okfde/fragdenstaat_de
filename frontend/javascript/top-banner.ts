import { toggleSlide } from 'froide/frontend/javascript/lib/misc'

interface IDonationBannerStore { timestamp: number }

function showTopBanner (): void {
  window._paq = window._paq ?? []

  function hideBanner (el: HTMLElement, code: string, time: number) {
    return (e: Event) => {
      e.preventDefault()
      window._paq?.push(['trackEvent', 'ads', 'topBanner', code])
      window.localStorage.setItem(itemName, JSON.stringify({
        timestamp: time
      }))
      if (hasAnimation) {
        toggleSlide(el)
        window.setTimeout(() => {
          removeBanner()
        }, 5 * 1000)
      } else {
        removeBanner()
      }
    }
  }
  function removeBanner (): void {
    if (topBanner.parentNode != null) {
      topBanner.parentNode.removeChild(topBanner)
    }
  }

  const els = document.querySelectorAll('.top-banner')
  if (els.length !== 1) {
    return
  }
  const topBanner = els[0] as HTMLElement

  const path = document.location.pathname
  if (['/spenden/',
    '/gesendet/',
    '/payment/',
    '/abgeschlossen/',
    '/anfrage-stellen/',
    '/account/'].some(p => path.includes(p))) {
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

  const itemName = 'top-banner'
  const now = (new Date()).getTime()
  const data = window.localStorage.getItem(itemName)
  if (data !== null) {
    const last = JSON.parse(data) as IDonationBannerStore
    if ((last.timestamp !== 0) && (now - last.timestamp) < (60 * 60 * 24 * 1000)) {
      return removeBanner()
    }
  }
  window.localStorage.removeItem(itemName)

  const closeButtons = topBanner.querySelectorAll('.banner-close')

  Array.from(closeButtons).forEach(closeButton => {
    closeButton.addEventListener('click', hideBanner(topBanner, 'close', now))
  })

  const cancel = topBanner.querySelector('.cancel-donation')
  const already = topBanner.querySelector('.already-donation')

  if (cancel != null) {
    cancel.addEventListener('click', hideBanner(topBanner, 'notnow', now))
  }
  if (already != null) {
    already.addEventListener('click', hideBanner(topBanner, 'donated', now + (1000 * 60 * 60 * 24 * 30)))
  }

  const dropdownBanner = topBanner.querySelector('.dropdown-banner') as HTMLElement
  const hasAnimation = dropdownBanner !== null
  if (dropdownBanner === null) {
    return
  }

  topBanner.style.display = 'none'
  topBanner.style.zIndex = '900'
  dropdownBanner.style.display = 'block'

  window.setTimeout(() => {
    window._paq?.push(['trackEvent', 'ads', 'topBanner', 'shown'])
    if (window.innerWidth > 768) {
      topBanner.style.position = 'sticky'
      topBanner.style.top = '0'
    }
    toggleSlide(topBanner)
  }, 3000)
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', showTopBanner)
} else {
  showTopBanner()
}
