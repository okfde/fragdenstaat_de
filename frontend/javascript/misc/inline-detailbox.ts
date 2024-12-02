const containers = document.querySelectorAll('.inline_detailbox')
containers.forEach((container) => {
    const template = container.getElementsByTagName('template')[0];
    container.addEventListener('click', () => {
        if (container.toggleAttribute("expanded")) {
            container.appendChild(template.content.cloneNode(true));
        } else {
            for (const elem of container.getElementsByClassName("inline_detailbox--content")) { container.removeChild(elem) }
        }
    })
  })
