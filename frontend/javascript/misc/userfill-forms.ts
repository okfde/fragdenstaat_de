if (document.body.dataset.user) {
  const userFillInputs = document.querySelectorAll('form[data-userfill] input');
  (Array.from(userFillInputs) as HTMLInputElement[]).forEach(input => {
    let name = input.name
    let val = document.body.dataset[`user${name}`]
    if (val) {
      input.value = val
    }
  })
}