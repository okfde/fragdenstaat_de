(function () {
  var btn = document.getElementById('load-contact-form')
  if (!btn) return
  btn.addEventListener('click', function () {
    var container = document.getElementById('contact-form-container')
    var url = container.getAttribute('data-form-url')
    btn.disabled = true
    fetch(url, { credentials: 'same-origin' })
      .then(function (response) {
        return response.text()
      })
      .then(function (html) {
        container.innerHTML = html
      })
      .catch(function () {
        btn.disabled = false
      })
  })
})()
