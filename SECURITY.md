# Security and data handling

This is a single-user local research application. The workbench binds only to
`127.0.0.1`, serves explicit routes/media IDs, and has no uploads, authentication
service, telemetry or external browser dependencies. It is not a public web server.

No API keys or cloud credentials are required. Competition assets, target labels,
predictions, private viewer exports and logs must stay outside Git history, even
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
