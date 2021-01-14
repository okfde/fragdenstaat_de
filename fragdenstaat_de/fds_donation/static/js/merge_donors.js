(function(){

  function applyValue (valueElement) {
    var fieldName = valueElement.dataset.field
    var value = valueElement.dataset.value
    var el = document.querySelector(`[name="${fieldName}"]`)
    el.value = value
  }
  
  Array.from(document.querySelectorAll('[data-donor]')).forEach(p => {
    p.style.cursor = 'copy'
    p.addEventListener('click', () => applyValue(p))
  })
  
  }())