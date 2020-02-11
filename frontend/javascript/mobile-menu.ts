const menuElement = document.querySelector('.mobile-menu')
const toggleButton = document.querySelector('.mobile-menu__toggle')
const menuContent = document.querySelector('.mobile-menu__wrapper') as HTMLElement
const backdropElement = document.querySelector('.mobile-menu__backdrop') as HTMLElement
const dropdownTriggers = document.querySelectorAll('.header-dropdown-trigger')

function init() {
  // event for toggle button
  toggleButton?.addEventListener('click', toggleMobileMenu)
  
  // event for backdrop click
  backdropElement.addEventListener('click', closeMobileMenu)

  // dropdown click events
  for (let i = 0, l = dropdownTriggers.length; i < l; i++) {
    const trigger: Element = dropdownTriggers[i]
    trigger.addEventListener('click', (e) => {
      triggerDrowdownMenu(e, trigger)
    })
  }
}

function isOpen () {
  return menuElement?.classList.contains('mobile-menu--visible')
}

function toggleMobileMenu() {
  if (isOpen()) {
    closeMobileMenu()
  } else {
    openMobileMenu()
  }
}

function closeMobileMenu () {
  // reset <body> tag, remove class
  document.body.style.overflow = 'auto'
  menuElement?.classList.remove('mobile-menu--visible')
}

function openMobileMenu () {
  // remove inital class once
  const inititalClassName = 'mobile-menu__wrapper--inital'
  if (menuContent?.classList.contains(inititalClassName)) {
    menuContent?.classList.remove(inititalClassName)
  }
  // hide overflown content for <body> tag, add class
  document.body.style.overflow = 'hidden'
  menuElement?.classList.add('mobile-menu--visible')
}

function triggerDrowdownMenu(e: Event, trigger: Element) {
  e.preventDefault()

  // find dropdown menu next to trigger
  const menu: (Element | null) = trigger.nextElementSibling  

  if (menu === null) return
  if (dropdownIsOpen(menu)) closeDropdown(trigger, menu)
  else openDropdown(trigger, menu)
  // add border to trigger
  // trigger.classList.add('border-bottom border-blue-800')
  
  
}

function dropdownIsOpen(dropdownElement: Element) {
  return dropdownElement.classList.contains('header-dropdown-content--visible')
}

function openDropdown(trigger: Element, dropdownElement: Element) {
  // add bg color
  trigger.classList.add('bg-light')
  dropdownElement.classList.add('bg-light')
  // add visible class
  dropdownElement.classList.add('header-dropdown-content--visible')
}

function closeDropdown(trigger: Element, dropdownElement: Element) {
  // remove bg color
  trigger.classList.remove('bg-light')
  dropdownElement.classList.remove('bg-light')
  // add visible class
  dropdownElement.classList.remove('header-dropdown-content--visible')
}



init()