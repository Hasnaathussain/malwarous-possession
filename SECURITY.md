# Security and data handling

The analysis workbench is a single-user local research application. It binds only to
`127.0.0.1`, serves explicit routes/media IDs, and has no uploads, authentication
service, telemetry or external browser dependencies. It is not a public web server.

Possession Atlas (`website/`) is a separate static public site. It serves only
approved licensed external replays and synthetic fixtures, with no backend,
uploads, credentials or browser package dependencies. Its Vercel configuration
restricts scripts and network requests to its own origin, forbids framing and
disables camera/microphone/location permissions. The optional local website
preview binds to loopback, rejects hidden/out-of-root files and supports media
byte ranges. Hosting must use `website/` as its root, never the research workspace.

No API keys or cloud credentials are required. Competition assets, target labels,
private viewer exports, other predictions and logs must stay outside Git history, even
while the repository is private. The organizer requires public code access for
submission; private visibility does not change the assets' redistribution terms.

The included joblib artifact is loaded only from its fixed path after its expected
SHA256, config, report and source checks. Do not substitute an untrusted model or
unpickle arbitrary files. These hashes detect changes; they are not a signature
from an independent party. Obtain the repository from the team's recorded source.

Use the pinned Python/dependency environment. Changes to the frozen inference
source or dependencies need a new reviewed, reproducible release rather than a
silent lock update. The Python socket guard is application-level, not an OS firewall.

Before committing, run `python -B scripts/verify_repository.py` after staging the
reviewed inventory. It rejects extra staged files and changed manifest bytes,
then verifies the frozen model/report/source. Do not force-add ignored outputs.

Report a suspected vulnerability privately to the repository owner. Include a
minimal synthetic reproduction; do not attach credentials or competition data.

The team explicitly requested publication of the final `submission/Malwarous.csv`
and `submission/Malwarous.pdf`. This exact packet is the exception to prediction
exclusion; it does not include raw video, tracking or private viewer material.

## Optional deployment analytics

A concurrent team-merged Vercel Analytics PR is preserved through the official plain-HTML script integration. It is isolated from replay startup, disabled on loopback and automated browsers, and removes replay query/hash parameters from page-view URLs. If deployment analytics is disabled, replay still works. No match coordinates, predictions, model inputs or form data are passed to analytics. The site keeps its self-origin CSP; no npm package installation is needed.
