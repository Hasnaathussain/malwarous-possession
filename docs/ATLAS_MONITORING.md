# Possession Atlas monitoring

Checked against Vercel's current documentation on 2026-11-16.

## Scope

Possession Atlas is a static site. It has no model-serving endpoint, application API, Vercel Function, or Routing Middleware. Monitoring therefore covers page visits, browser performance, deployment builds, and Vercel's CDN request data. There is no server application runtime or model trace to instrument. Do not add logging that presents synthetic fixtures or replay/frame state as production inference activity.

## Browser signals

[`website/analytics.js`](../website/analytics.js) loads Vercel's plain-HTML Web Analytics and Speed Insights scripts as separate optional integrations. It uses the same-origin paths `/_vercel/insights/script.js` and `/_vercel/speed-insights/script.js`; it adds no npm dependency and makes no blocking call.

Both Vercel `beforeSend` callbacks reduce each event URL to its origin and pathname, removing the entire query string and fragment before the event is sent. An unparseable URL is dropped. No custom events are emitted, and the page does not send replay identity, frame time, possession labels, or model outputs. Each script is loaded asynchronously, removed if loading fails, and handled independently so an unavailable or disabled telemetry route does not interrupt the site.

The loader preserves the existing gates: it runs only on a `*.vercel.app` hostname and skips browsers with `navigator.webdriver`. Local previews on other hosts and automated browser sessions do not send these browser events.

### Current project status

At the dashboard check on 2026-11-16, Web Analytics was already enabled and showed one visitor and two page views. Speed Insights was enabled but had no events yet; the plain-HTML Speed Insights client was not in the deployed site. This change adds that client. The current project is on Hobby; custom Web Analytics events require Pro or Enterprise, so this implementation sends none and does not require an upgrade.

## Vercel dashboard setup

The current project already has Web Analytics and Speed Insights enabled. For a new project or if either setting is later disabled:

1. In Vercel, open the project and enable **Web Analytics** from its Analytics page.
2. Enable **Speed Insights** from its project page.
3. Deploy after enabling either feature so Vercel installs the collection routes.
4. Confirm the browser loads `/_vercel/insights/script.js` and `/_vercel/speed-insights/script.js` from the site's own origin. Check the Analytics and Speed Insights pages in the project dashboard after visits.

Speed Insights may send its measurement after a page blur or unload, so check after navigating away or switching tabs. An ad blocker can prevent its script or requests. Web Analytics and Speed Insights are available on all Vercel plans, with plan-specific quotas and limits; enabling them here does not authorize a paid plan or add-on upgrade.

## Native platform observability

- **Build logs:** Each deployment has Vercel build logs showing build-tool versions, warnings/errors, and installed or generated files. Open the deployment in the Vercel dashboard and inspect its build log. Vercel documents Build Logs as available on all plans.
- **CDN requests:** Vercel Observability's CDN Requests data is the request-level view for this static site. A static asset request creates a CDN request event. Use the project dashboard's Observability views for traffic, status, and cache behavior.
- **Runtime logs:** Vercel Runtime Logs primarily contain Vercel Function and Routing Middleware execution output. They include only a subset of static requests (static requests that serve cache); they are not a complete request ledger for this static site. Since this project has no functions or middleware, there are no application runtime logs or server span traces to inspect.
- **Plan boundaries:** Basic Observability is available on all plans. Observability Plus, longer retention, expanded metrics, and Log Drains are separate plan/add-on capabilities. No paid upgrade, drain, or custom event is part of this setup.

## Official references

- [Web Analytics quickstart](https://vercel.com/docs/analytics/quickstart) — plain HTML queue, dashboard enablement, and collection routes.
- [Web Analytics overview](https://vercel.com/docs/analytics) — plan availability and dashboard metrics.
- [Web Analytics client configuration](https://vercel.com/docs/analytics/package) — `beforeSend` and URL redaction.
- [Speed Insights quickstart](https://vercel.com/docs/speed-insights/quickstart) — plain HTML queue, enablement, and collection routes.
- [Speed Insights client configuration](https://vercel.com/docs/speed-insights/package) — `beforeSend` and script configuration.
- [Speed Insights troubleshooting](https://vercel.com/docs/speed-insights/troubleshooting) — timing and blocked-script checks.
- [Vercel Observability](https://vercel.com/docs/observability) — CDN request events and plan boundaries.
- [Vercel logs](https://vercel.com/docs/logs) and [Runtime Logs](https://vercel.com/docs/logs/runtime) — build/runtime log scope and static-request coverage.
