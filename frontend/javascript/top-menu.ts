// const menuContainer = document.querySelector('.top-menu')
// const menuDropdownTriggers = document.querySelectorAll('.top-menu__dropdown-trigger')

// function initTopMenu() {
//   // dropdown click/hover events
//   for (let i = 0, l = menuDropdownTriggers.length; i < l; i++) {
//     const trigger: Element = menuDropdownTriggers[i]
//     trigger.addEventListener('mouseover', (e) => {
//       triggerDrowdownMenu(e, trigger)
//     })
//   }
// }


// function triggerDrowdownMenu(e: Event, trigger: Element) {
//   e.preventDefault()

//   // find dropdown menu next to trigger
//   const menu: (Element | null) = trigger.nextElementSibling

//   if (menu === null) return
//   if (dropdownIsOpen(menu)) closeDropdown(menu)
//   else openDropdown(menu)
// }


// function isOpen() {
//   return drawerContainer?.classList.contains('drawer-menu--visible')
// }

// function toggleDrawerMenu() {
//   if (isOpen()) {
//     closeDrawerMenu()
//   } else {
//     openDrawerMenu()
//   }
// }

// function closeDrawerMenu() {
//   // reset <body> tag, remove class
//   document.body.style.overflow = 'auto'
//   drawerContainer?.classList.remove('drawer-menu--visible')
// }

// function openDrawerMenu() {
//   // remove inital class once
//   const inititalClassName = 'drawer-menu__wrapper--inital'
//   if (drawerWrapper?.classList.contains(inititalClassName)) {
//     drawerWrapper?.classList.remove(inititalClassName)
//   }
//   // hide overflown content for <body> tag, add class
//   document.body.style.overflow = 'hidden'
//   drawerContainer?.classList.add('drawer-menu--visible')
//   // scroll top
//   if (drawerWrapper !== null) drawerWrapper.scrollTop = 0

// }

// function dropdownIsOpen(dropdownElement: Element) {
//   return dropdownElement.classList.contains('drawer-menu__dropdown-content--visible')
// }

// function openDropdown(dropdownElement: Element) {
//   // add visible class
//   dropdownElement.classList.add('drawer-menu__dropdown-content--visible')
// }

// function closeDropdown(dropdownElement: Element) {
//   // add visible class
//   dropdownElement.classList.remove('drawer-menu__dropdown-content--visible')
// }



// initTopMenu()