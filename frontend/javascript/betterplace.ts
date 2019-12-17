const betterplaceProgress = document.querySelectorAll(".betterplace-progress");

Array.from(betterplaceProgress).forEach((el) => {
  const dataset = (el as HTMLElement).dataset;
  const bar = el.querySelector(".progress-bar") as HTMLElement;
  if (bar === null) {
    return;
  }
  const url = dataset.url;
  if (!url) {
    return;
  }
  window.fetch(url).then((response) => response.json()).then((data) => {
    bar.style.width = `${data.progress_percentage}%`;
    bar.textContent = `${Math.floor(parseFloat(data.progress_percentage))}%`;

    const openLabel = el.querySelector(".open-amount") as HTMLElement;
    if (openLabel) {
      openLabel.textContent = `${Math.floor(data.open_amount_in_cents / 100)}`;
    }

  });
});
