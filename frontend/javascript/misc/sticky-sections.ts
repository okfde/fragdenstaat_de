const stickyContainers: NodeListOf<HTMLElement> = document.querySelectorAll('.sticky-section-container')

stickyContainers.forEach(container => {
  const bulletContainer = document.createElement('div')
  bulletContainer.classList.add('sticky-section-bullets')

  const bullets = document.createElement('div')
  bullets.classList.add('glide__bullets')

  const sections = container.querySelectorAll('.sticky-section');
  sections.forEach((section, i) => {
    const firstChild = section.firstElementChild as HTMLElement;
    if (!firstChild) return

    const bullet = document.createElement('button')
    bullet.classList.add('glide__bullet')
    if (i === 0) bullet.classList.add('glide__bullet--active')

    bullet.addEventListener('click', () => {
      const top = container.offsetHeight / 3 * i + container.offsetTop;
      window.scrollTo({ top, behavior: 'smooth' })
      if (firstChild.id) window.history.pushState(undefined, '', `#${firstChild.id}`)
    })

    bullets.appendChild(bullet)

    new IntersectionObserver(([e]) => {
      Array.from(bullets.children).forEach(el => el.classList.remove('glide__bullet--active'))

      if (e.intersectionRatio > 0) {
        bulletContainer.classList.add('visible')
        bullet.classList.add('glide__bullet--active')
      } else if (i === 0) {
        bulletContainer.classList.remove('visible')
      } else {
        bullets.children[i - 1].classList.add('glide__bullet--active')
      }
    }).observe(firstChild)
  })

  bulletContainer.appendChild(bullets)
  container.appendChild(bulletContainer)
})