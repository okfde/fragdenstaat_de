const containers = document.querySelectorAll('.shuffle-items')
containers.forEach(container => {
  for (let i = container.children.length; i >= 0; i--) {
    container.appendChild(container.children[Math.random() * i | 0]);
  }
})