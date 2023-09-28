import transitionDone from './misc/await-transition'

const header = document.querySelector('#header')!
let counter = 0

header.querySelectorAll<HTMLElement>('.nav-toggle-menu').forEach((el) =>
  el.addEventListener('click', async () => {
    const targetName = el.dataset.target
    if (targetName == null) return

    const target = header.querySelector<HTMLElement>(`#menu-${targetName}`)
    if (target == null) return

    // hide other navs
    const otherNavs = header.querySelectorAll('.nav-menu')
    otherNavs.forEach((el) => el !== target && el.classList.remove('show'))
    await transitionDone(otherNavs)

    const otherTriggers = header.querySelectorAll('a[data-target]')
    otherTriggers.forEach((el) => el.setAttribute('aria-expanded', 'false'))

    const dropdown = updateDropdown()
    if (dropdown) {
      dropdown.show()
      return
    }

    target.classList.toggle('show')
    target.classList.remove('d-none')
    target.style.visibility = 'visible'

    el.setAttribute(
      'aria-expanded',
      target.classList.contains('show') ? 'true' : 'false'
    )

    counter++
    let id = counter

    const hide = () => {
      if (id === counter) {
        target.classList.remove('show')
        el.setAttribute('aria-expanded', 'false')
      }
    }
    window.addEventListener('resize', hide, { once: true })

    window.requestAnimationFrame(() => {
      window.addEventListener('click', (e) => {
        console.log(e)
        if (!target.contains(e.target as Element)) hide()
      })
    })

    window.addEventListener('scroll', () => {
      if (window.scrollY > 150) hide()
    })
  })
)

function updateDropdown() {
  const target = document.querySelector('#menu-user')!
  const el = target.parentElement!
  const trigger = el.querySelector('button')!

  if (window.innerWidth < 768) {
    el.classList.remove('dropdown')
    target?.classList.remove('dropdown-menu')
    trigger.removeAttribute('data-bs-toggle')
    trigger.classList.remove('dropdown-toggle')
    const dropdown = window.bootstrap.Dropdown.getInstance(trigger)
    dropdown?.dispose()
  } else {
    el.classList.add('dropdown')
    trigger.setAttribute('data-bs-toggle', 'dropdown')
    trigger.classList.add('dropdown-toggle')
    target?.classList.add('dropdown-menu')
    return window.bootstrap.Dropdown.getOrCreateInstance(trigger)
  }
}

window.addEventListener('resize', updateDropdown)
updateDropdown()
