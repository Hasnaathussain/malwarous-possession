// Separate, optional Vercel Web Analytics. A missing endpoint cannot stop the replay.
// Plain-HTML integration: https://vercel.com/docs/analytics/quickstart
(() => {
  if (!location.hostname.endsWith('.vercel.app') || navigator.webdriver) return;
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  // Public replay deep-link parameters are not needed for page-view measurements.
  window.va('beforeSend', event => {
    const url = new URL(event.url); url.search = ''; url.hash = '';
    return {...event, url: url.href};
  });
  const script = document.createElement('script');
  script.defer = true;
  script.src = '/_vercel/insights/script.js';
  script.onerror = () => { script.remove(); }; // Deployment analytics may be disabled.
  document.head.append(script);
})();
