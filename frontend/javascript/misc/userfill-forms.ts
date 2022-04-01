if (document.body.dataset.user === undefined) {
  document
    .querySelectorAll<HTMLInputElement>('form[data-userfill] input')
    .forEach((input) => {
      const name = input.name
      const val = document.body.dataset[`user${name}`]
      if (val !== undefined) {
        input.value = val
      }
    })
}
