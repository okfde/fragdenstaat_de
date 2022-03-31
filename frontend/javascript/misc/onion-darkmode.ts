if (document.location.hostname.includes('.onion')) {
  // document.body.classList.add("darkmode");
  document.body.classList.add('onion-site')
  const root = document.getElementsByTagName('html')[0]
  root.setAttribute('class', 'darkmode')
}
