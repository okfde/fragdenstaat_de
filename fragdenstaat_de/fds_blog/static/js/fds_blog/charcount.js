(function () {
  const ID_POSTFIX = "__charcount";
  const fields = JSON.parse(document.getElementById('charcount-fields').textContent)

  fields.forEach(name => {
    const element = document.getElementById(`id_${name}`)
    setupCharCount(element)
  });


  function getCounter(el) {
    const span = document.getElementById(el.id + ID_POSTFIX)
    const wordCount = el.value.split(/\s+/).length
    if (el.maxLength && el.maxLength !== -1) {
      span.innerText = `${el.value.length}/${el.maxLength} – ${wordCount}`
    } else {
      span.innerText = `${el.value.length} – ${wordCount}`
    }
  }

  function setupCharCount(element) {
    const parent = element.parentElement
    const span = document.createElement("span")
    span.className = "admin-charcounter"
    span.id = element.id + ID_POSTFIX
    span.style.color = "lightgray"
    span.style.float = "right"
    parent.appendChild(span)
    element.addEventListener("keyup", function () {
      getCounter(this)
    })
    getCounter(element)
  }

}())