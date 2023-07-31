import Glide from '@glidejs/glide'

window.onload = () => {
  const glides = document.querySelectorAll('.glide')
  Array.from(glides).forEach((el) => {
    let options = {}
    if (el.dataset.options) {
      try {
        options = JSON.parse(el.dataset.options)
      } catch {
        console.error('Could not parse options', el.dataset.options)
      }
    }
    new Glide(el, options).mount()
  })
}
