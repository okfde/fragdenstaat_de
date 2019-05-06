import 'froide/frontend/javascript/request.ts'


const container = document.querySelector('#glyphosat-download .modal-content')
const el = document.querySelector('#glyphosat-download-form')
if (container && el) {
  el.addEventListener('submit', () => {
    window.setTimeout(() => {
      container.innerHTML = '<div class="text-center"><h3>Gutachten wird geladen...</h3><img src="https://media.frag-den-staat.de/files/media/main/13/2c/132cf116-f09b-4498-8429-2cbbf96b9f8b/keyboard-cat.gif" alt="Loading"/></div>'
    }, 300)
  })
}
