import { Modal } from 'bootstrap'

const searchModal = document.getElementById('search-modal')

if (searchModal != null) {
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault()
      new Modal(searchModal).show()
    }
  })
}
