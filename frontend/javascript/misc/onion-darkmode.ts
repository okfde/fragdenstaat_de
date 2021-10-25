if (document.location.hostname.indexOf(".onion") !== -1) {
  // document.body.classList.add("darkmode");
  document.body.classList.add("onion-site");
  const root = document.getElementsByTagName("html")[0];
  root.setAttribute("class", "darkmode");
}