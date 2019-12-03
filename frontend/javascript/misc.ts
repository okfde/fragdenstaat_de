window.addEventListener("message", (e) => {
  if (e.origin !== "https://okfde.github.io" && e.origin !== "http://127.0.0.1:8001") { return; }
  if (e.data[0] !== "setIframeHeight") { return; }
  const iframeId = e.data[1];
  const iframe = document.getElementById(iframeId);
  if (iframe !== null) {
    iframe.style.height = e.data[2] + "px";
  }
}, false);

window.document.addEventListener("securitypolicyviolation", (e) => {
  if (e.violatedDirective.indexOf("script") !== -1 && e.blockedURI.indexOf("https://data1.") !== -1) {
    window.alert("Liebe/r Nutzer/in,\noffenbar versucht eine Ihrer Browser-Erweiterungen Sie vermutlich ohne Ihre Kenntnis zu tracken.\n\nWir raten Ihnen Browser-Erweiterungen zu deinstallieren, die Sie nicht nutzen.");
  }
});

(function () {
  const videoEmbed = document.querySelector(".video-embed");
  if (videoEmbed !== null) {
    videoEmbed.addEventListener("click", function(this: HTMLElement, e) {
      e.preventDefault();
      const parent = this.parentElement;
      if (parent !== null && this.dataset.url) {
        const iframe = document.createElement("iframe");
        iframe.src = this.dataset.url;
        iframe.setAttribute("frameBorder", "0");
        iframe.setAttribute("webkitallowfullscreen", "");
        iframe.setAttribute("mozallowfullscreen", "");
        iframe.setAttribute("allowfullscreen", "");
        parent.appendChild(iframe);
        if (this.dataset.vimeosubtitlelanguage) {
          const lang = this.dataset.vimeosubtitlelanguage;
          const origin = this.dataset.url.split("/").slice(0, 3).join("/");
          const setLanguage = () => {
            if (!iframe.contentWindow) { return; }
            iframe.contentWindow.postMessage({
              method: "enableTextTrack",
              value: {
                kind: "subtitles",
                language: lang,
              },
            }, origin);
          };
          iframe.addEventListener("load", setLanguage);
          window.setTimeout(setLanguage, 1000);
        }
      }
    });
  }
}());

interface Window { _paq: Array<Array<string | string[]>>; }

(function() {
  const MATOMO_DOMAIN = "https://traffic.okfn.de";

  window._paq = window._paq || [];
  window._paq.push(["trackPageView"]);
  window._paq.push(["enableLinkTracking"]);
  window._paq.push(["setDomains", ["*.fragdenstaat.de"]]);
  window._paq.push(["setTrackerUrl", `${MATOMO_DOMAIN}/matomo.php`]);
  window._paq.push(["setSiteId", "25"]);

  const script = document.createElement("script");
  script.type = "text/javascript";
  script.async = true;
  script.defer = true;
  script.src = `${MATOMO_DOMAIN}/matomo.js`;
  document.body.appendChild(script);
}());

if (document.location.hostname.indexOf(".onion") !== -1) {
  document.body.classList.add("darkmode");
  const root = document.getElementsByTagName("html")[0];
  root.setAttribute("class", "darkmode");
}
