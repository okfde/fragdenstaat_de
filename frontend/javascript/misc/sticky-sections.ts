const stickyContainers: NodeListOf<HTMLElement> = document.querySelectorAll('.sticky-section-container')

stickyContainers.forEach(container => {
  const bulletContainer = document.createElement('div')
  bulletContainer.classList.add('sticky-section-bullets')

  const bullets = document.createElement('div')
  bullets.classList.add('glide__bullets')

  const sections = container.querySelectorAll('.sticky-section');
  sections.forEach((section, i) => {
    const bullet = document.createElement('button')
    bullet.classList.add('glide__bullet')
    if (i === 0) bullet.classList.add('glide__bullet--active')

    bullet.addEventListener('click', () => {
      const { top } = section.getBoundingClientRect()
      window.scrollTo({ top, behavior: 'smooth' })
    })

    bullets.appendChild(bullet)

    const ob = new IntersectionObserver(([e]) => {
      console.log(e)

      Array.from(bullets.children).forEach(el => el.classList.remove('glide__bullet--active'))

      if (e.intersectionRatio > 0) {
        bulletContainer.classList.add('visible')
        bullet.classList.add('glide__bullet--active')
      } else if (i === 0) {
        bulletContainer.classList.remove('visible')
      } else {
        bullets.children[i - 1].classList.add('glide__bullet--active')
      }
    })
    ob.observe(section)
  })

  bulletContainer.appendChild(bullets)
  container.appendChild(bulletContainer)
})