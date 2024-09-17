function showTargetAnchor(): void {
  let el: HTMLElement | null = null
  try {
    el = document.querySelector<HTMLElement>(
      `.highlight-anchor ${window.location.hash}`
    )
  } catch {
    return
  }

  if (el != null) {
    el.classList.add('highlight')
    setTimeout(() => {
      if (el != null) {
        const { transition } = el.style
        el.style.transition = 'background-color 2s'
        el.classList.remove('highlight')

        el.addEventListener(
          'transitionend',
          () => {
            if (el != null) {
              el.style.transition = transition
            }
          },
          { once: true }
        )
      }
    }, 2000)
  }
}

if (window.location.hash !== '') {
  showTargetAnchor()
}
