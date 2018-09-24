(function () {
  var getHeight = function (el) {
    var el_style = window.getComputedStyle(el)
    var el_display = el_style.display
    var el_position = el_style.position
    var el_visibility = el_style.visibility
    var el_max_height = el_style.maxHeight.replace('px', '').replace('%', '')
    var wanted_height = 0

    // if its not hidden we just return normal height
    if (el_display !== 'none' && el_max_height !== '0') {
      return el.offsetHeight
    }

    // the element is hidden so:
    // making the el block so we can meassure its height but still be hidden
    el.style.position = 'absolute'
    el.style.visibility = 'hidden'
    el.style.display = 'block'

    wanted_height = el.offsetHeight

    // reverting to the original values
    el.style.display = el_display
    el.style.position = el_position
    el.style.visibility = el_visibility

    return wanted_height
  }

  /**
  * toggleSlide mimics the jQuery version of slideDown and slideUp
  * all in one function comparing the max-heigth to 0
   */
  var toggleSlide = function (el) {
    var elMaxHeight = 0

    if (el.getAttribute('data-max-height')) {
      // we've already used this before, so everything is setup
      if (el.style.maxHeight.replace('px', '').replace('%', '') === '0') {
        el.style.maxHeight = el.getAttribute('data-max-height')
      } else {
        el.style.maxHeight = '0'
      }
    } else {
      elMaxHeight = getHeight(el) + 'px'
      el.style['transition'] = 'max-height 2s ease-in-out'
      el.style.overflowY = 'hidden'
      el.style.maxHeight = '0'
      el.setAttribute('data-max-height', elMaxHeight)
      el.style.display = 'block'

      // we use setTimeout to modify maxHeight later than display (to we have the transition effect)
      setTimeout(function () {
        el.style.maxHeight = elMaxHeight
      }, 10)
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    window._paq = window._paq || []

    if (document.location.pathname.indexOf('/spenden/') !== -1 ||
        document.location.pathname.indexOf('/blog/') !== -1 ||
        document.location.pathname.indexOf('/anfrage-stellen/') !== -1 ||
        document.location.pathname.indexOf('/account/') !== -1) {
      return
    }
    var el = document.getElementById('donation-block')
    var cancel = document.getElementById('cancel-donation')
    var already = document.getElementById('already-donation')
    var header = document.getElementById('header')
    if (header === null) {
      return
    }
    if (!window.localStorage) {
      return
    }
    var itemName = 'donation-banner'
    var now = (new Date()).getTime()
    var last = window.localStorage.getItem(itemName)
    if (last !== null) {
      last = JSON.parse(last)
      if (last.timestamp && (now - last.timestamp) < (60 * 60 * 24 * 1000)) {
        return
      }
    }
    window.localStorage.removeItem(itemName)
    cancel.addEventListener('click', function (e) {
      e.preventDefault()
      window._paq.push(['trackEvent', 'donations', 'donationBanner', 'notnow'])
      window.localStorage.setItem(itemName, JSON.stringify({
        timestamp: now
      }))
      el.parentNode.removeChild(el)
    })
    already.addEventListener('click', function (e) {
      e.preventDefault()
      window._paq.push(['trackEvent', 'donations', 'donationBanner', 'donated'])
      window.localStorage.setItem(itemName, JSON.stringify({
        timestamp: now + (1000 * 60 * 60 * 24 * 30)
      }))
      el.parentNode.removeChild(el)
    })
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
  })
}())
