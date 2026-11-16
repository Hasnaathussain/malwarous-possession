# Possession semantics and the provider gap

The implementation is a learned approximation of the challenge's rules. Mapping
both providers to H/A/D does not establish that their underlying control and
stoppage conventions are equivalent.

## External supervision actually used

The six DFL/Sportec matches supply provider `BallStatus` and `BallPossession`.
`malwarous/external_sportec.py` maps status 0 to D, regardless of the owner field;
status 1 with possession 1/2 maps to H/A. Unknown status/owner values are excluded
from the corresponding supervised head. The owner head trains only on alive,
known-owner frames. These are source-provider fields, not new Malwarous annotations.
We do not claim independent verification of the provider's annotation workflow or
of equivalence to Metrica's corrected-tracking semantics.

## Challenge rule versus implementation

| Situation | Challenge requirement | What this pipeline implements |
| --- | --- | --- |
| Loose or contested live ball | Last controlled team retains possession until the opponent establishes control. | Learned H/A evidence and a fixed switching penalty favor persistence; there is no explicit loose-ball state or guaranteed last-owner hold. |
| Touch, deflection or aerial duel | Contact alone is insufficient for a turnover. | No contact detector, completed-pass counter or referee/control classifier; the decoded evidence path can still switch too early or late. |
| Stoppage | D, without ownership; a stoppage separates two spells even if the same team restarts. | A learned active/dead head supplies D evidence; missing ball coordinates alone do not force D. Source-provider stoppage semantics may differ. |
| Restart | A live restart has a possessor, after which control changes are inferred. | The learned live/owner heads and decoder determine the return to H/A. No Smart Tagging restart constraint or hard restart-team overwrite is used. |
| Unsupported or outside-half frame | X is abstention; outside-half frames are ungraded. | Official outside-half blocks are X. Inside each half the fixed decoder chooses H/A/D; it has no calibrated abstention policy. |

Viterbi operates on a whole half, with equal cost 10 for a state change and no hard
minimum spell duration. It resets between halves. Future context is used. Neither
the CSV nor its boundaries receive manual edits or target-specific time shifts.

The authoritative target definition is
[CHALLENGE.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/CHALLENGE.md).
Its labels mechanically inherit corrected Metrica alive/ownership values; they
are not established by our external labels. This unresolved semantic transfer
is a model limitation, not a claimed rule-compliance proof of prediction accuracy.

## What would strengthen the next version

Pre-register a fresh, chronologically separate match-level evaluation, including
conditional missingness near duels and camera exits. Qualify an independently
aligned restart channel before testing bounded tag priors. Approximate set-piece
windows must not be treated as exact D intervals. Evaluate short-spell recall and
timing alongside spellF1; do not set output counts or shifts from the public sample.
