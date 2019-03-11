const betterplaceProgress = document.querySelectorAll('.betterplace-progress')

Array.from(betterplaceProgress).forEach((el) => {
  const dataset = (<HTMLElement> el).dataset
  const bar = <HTMLElement> el.querySelector('.progress-bar')
  if (bar === null) {
    return
  }
  const url = dataset.url
  if (!url) {
    return
  }
  window.fetch(url).then(response => response.json()).then((data) => {
    bar.style.width = `${data.progress_percentage}%`
    bar.textContent = `${Math.floor(parseFloat(data.progress_percentage))}%`

    const openLabel = <HTMLElement> el.querySelector('.open-amount')
    if (openLabel) {
      openLabel.textContent = `${Math.floor(data.open_amount_in_cents / 100)}`
    }

  })
})