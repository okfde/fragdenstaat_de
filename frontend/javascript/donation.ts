import { toggleSlide } from 'froide/frontend/javascript/lib/misc'

interface DonationBannerStore { timestamp: number; }

function showDonationBanner () {
  window._paq = window._paq || []

  function hideBanner (code: string, time: number) {
    return function (e: Event) {
      e.preventDefault()
      window._paq.push(['trackEvent', 'donations', 'donationBanner', code])
      window.localStorage.setItem(itemName, JSON.stringify({
        timestamp: time
      }))
      toggleSlide(el)
      window.setTimeout(function () {
        el.parentNode && el.parentNode.removeChild(el)
      }, 5 * 1000)
    }
  }

  if (document.location && document.location.pathname) {
    if (document.location.pathname.indexOf('/spenden/') !== -1 ||
        document.location.pathname.indexOf('/blog/') !== -1 ||
        document.location.pathname.indexOf('/anfrage-stellen/') !== -1 ||
        document.location.pathname.indexOf('/account/') !== -1) {
      return
    }
  }
  const els = document.querySelectorAll('.donation-block')
  if (els.length === 2) {
    let demoEl = <HTMLElement> els[1]
    demoEl.style.display = 'block'
    return
  }
  if (els.length !== 1) {
    return
  }
  const el = <HTMLElement> els[0]
  if (!window.localStorage) {
    return
  }
  const cancel = el.querySelector('.cancel-donation')
  const already = el.querySelector('.already-donation')
  const close = el.querySelector('.close')

  const itemName = 'donation-banner'
  const now = (new Date()).getTime()
  const data = window.localStorage.getItem(itemName)
  if (data !== null) {
    const last = <DonationBannerStore> JSON.parse(data)
    if (last.timestamp && (now - last.timestamp) < (60 * 60 * 24 * 1000)) {
      return
    }
  }
  window.localStorage.removeItem(itemName)

  if (close) {
    close.addEventListener('click', hideBanner('close', now))
  }

  if (cancel) {
    cancel.addEventListener('click', hideBanner('notnow', now))
  }
  if (already) {
    already.addEventListener('click', hideBanner('donated', now + (1000 * 60 * 60 * 24 * 30)))
  }
  window.setTimeout(function () {
    window._paq.push(['trackEvent', 'donations', 'donationBanner', 'shown'])
    if (window.innerWidth > 768) {
      el.style.position = 'sticky'
      el.style.top = '0'
    }
    toggleSlide(el)
    window.setTimeout(function () {
    }, 2000)
  }, 3000)
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', showDonationBanner)
} else {
  showDonationBanner()
}
