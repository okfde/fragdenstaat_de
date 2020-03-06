const drawerContainer = document.querySelector(".drawer-menu");
const drawerWrapper = document.querySelector(".drawer-menu__wrapper");
const drawerToggleButton = document.querySelector(".drawer-menu__toggle");
const backdropElement = document.querySelector(".drawer-menu__backdrop");
const drawerDropdownTriggers = document.querySelectorAll(".drawer-menu__dropdown-trigger");

function initDrawerMenu() {
  // event for toggle button
  drawerToggleButton?.addEventListener("click", toggleDrawerMenu);
  // event for backdrop click
  backdropElement?.addEventListener("click", closeDrawerMenu);

  // dropdown click events
  for (let i = 0, l = drawerDropdownTriggers.length; i < l; i++) {
    const trigger: Element = drawerDropdownTriggers[i];
    trigger.addEventListener("click", (e) => {
      triggerDrowdownMenu(e, trigger);
    });
  }
}

function isOpen() {
  return drawerContainer?.classList.contains("drawer-menu--visible");
}

function toggleDrawerMenu() {
  if (isOpen()) {
    closeDrawerMenu();
  } else {
    openDrawerMenu();
  }
}

function closeDrawerMenu() {
  // reset <body> tag, remove class
  document.body.style.overflow = "auto";
  drawerContainer?.classList.remove("drawer-menu--visible");
}

function openDrawerMenu() {
  // remove inital class once
  const inititalClassName = "drawer-menu__wrapper--inital";
  if (drawerWrapper?.classList.contains(inititalClassName)) {
    drawerWrapper?.classList.remove(inititalClassName);
  }
  // hide overflown content for <body> tag, add class
  document.body.style.overflow = "hidden";
  drawerContainer?.classList.add("drawer-menu--visible");
  // scroll top
  if (drawerWrapper !== null) { drawerWrapper.scrollTop = 0; }

}

function triggerDrowdownMenu(e: Event, trigger: Element) {
  e.preventDefault();

  // find dropdown menu next to trigger
  const menu: (Element | null) = trigger.nextElementSibling;

  if (menu === null) { return; }
  if (dropdownIsOpen(menu)) { closeDropdown(menu); } else { openDropdown(menu); }
}

function dropdownIsOpen(dropdownElement: Element) {
  return dropdownElement.classList.contains("drawer-menu__dropdown-content--visible");
}

function openDropdown(dropdownElement: Element) {
  // add visible class
  dropdownElement.classList.add("drawer-menu__dropdown-content--visible");
}

function closeDropdown(dropdownElement: Element) {
  // add visible class
  dropdownElement.classList.remove("drawer-menu__dropdown-content--visible");
}

initDrawerMenu();
