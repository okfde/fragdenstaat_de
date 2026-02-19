;(function () {
  function applyValue(valueElement) {
    var fieldName = valueElement.dataset.field
    var value = valueElement.dataset.value
    var el = document.querySelector(`[name="${fieldName}"]`)
    if (el.tagName === 'SELECT') {
      if (value === '' && el.querySelector("option[value='']")) {
        el.value = ''
      } else if (value === '') {
        el.value = 'unknown'
      } else if (
        el.querySelector("option[value='" + value.toLowerCase() + "']")
      ) {
        el.value = value.toLowerCase()
      } else {
        el.value = value
      }
    } else {
      el.value = value
    }
  }

  document.querySelectorAll('[data-donor]').forEach((p) => {
    p.style.cursor = 'copy'
    p.addEventListener('click', () => applyValue(p))
  })
})()
