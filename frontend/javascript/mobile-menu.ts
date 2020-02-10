const menuElement = document.querySelector('.mobile-menu')
const toggleButton = document.querySelector('.mobile-menu__toggle')
const menuContent = document.querySelector('.mobile-menu__wrapper') as HTMLElement
const backdropElement = document.querySelector('.mobile-menu__backdrop') as HTMLElement

function init() {
  // event for toggle button
  toggleButton?.addEventListener('click', toggleMobileMenu)
  
  // event for backdrop click
  backdropElement.addEventListener('click', closeMobileMenu)
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

init()