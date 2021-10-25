window.document.addEventListener("securitypolicyviolation", (e) => {
  if (e.violatedDirective.indexOf("script") !== -1 && e.blockedURI.indexOf("https://data1.") !== -1) {
    window.alert(`Liebe/r Nutzer/in,\noffenbar versucht eine Ihrer Browser-Erweiterungen Sie vermutlich ohne
    Ihre Kenntnis zu tracken.
    \n\nWir raten Ihnen Browser-Erweiterungen zu deinstallieren, die Sie nicht nutzen.`);
  }
});