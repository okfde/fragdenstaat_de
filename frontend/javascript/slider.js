import Glide from '@glidejs/glide'

document.onreadystatechange = function () {
  if (document.readyState !== 'loading') {
    const glides = document.querySelectorAll('.glide')
    Array.from(glides).forEach((el) => {
      let options = {}
      if (el.dataset.options) {
        try {
          options = JSON.parse(el.dataset.options)
        } catch {}
      }
      new Glide(el, options).mount()
    })
  }
}