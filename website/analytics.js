// Optional, independent Vercel Web Analytics and Speed Insights loaders.
// Page URLs are reduced to origin + pathname before either event is sent.
(() => {
  if (!location.hostname.endsWith(".vercel.app") || navigator.webdriver) return;

  const redactUrl = (event) => {
    if (!event || typeof event.url !== "string") return null;
    try {
      const url = new URL(event.url, location.href);
      url.search = "";
      url.hash = "";
      return { ...event, url: url.href };
    } catch {
      // Drop unparseable events instead of sending an unredacted URL.
      return null;
    }
  };

  const install = (globalName, queueName, scriptPath) => {
    let script = null;
    try {
      window[globalName] = window[globalName] || function () {
        (window[queueName] = window[queueName] || []).push(arguments);
      };
      window[globalName]("beforeSend", redactUrl);

      script = document.createElement("script");
      script.async = true;
      script.src = scriptPath;
      script.onerror = () => script.remove();
      document.head.append(script);
    } catch {
      // Optional telemetry must not interrupt the static site. Each loader fails alone.
      if (script) script.remove();
    }
  };

  install("va", "vaq", "/_vercel/insights/script.js");
  install("si", "siq", "/_vercel/speed-insights/script.js");
})();
