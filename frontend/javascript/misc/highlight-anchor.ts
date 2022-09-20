if (window.location.hash !== '') {
  const el = document.querySelector<HTMLElement>(
    `.highlight-anchor ${window.location.hash}`
  )

  if (el != null) {
    el.classList.add('highlight')
    setTimeout(() => {
      const { transition } = el.style
      el.style.transition = 'background-color 2s'
      el.classList.remove('highlight')

      el.addEventListener(
        'transitionend',
        () => {
          el.style.transition = transition
        },
        { once: true }
      )
    }, 2000)
  }
}
