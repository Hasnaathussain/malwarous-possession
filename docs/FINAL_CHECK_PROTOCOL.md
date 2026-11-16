# Frozen-output pipeline check

Registered 16 November 2026, before running this check. This is a correctness
check, not a new experiment or a model-selection gate.

## Fixed inputs and boundary

- Frozen inference source anchor: `b616105457a77cc4ad74324ce333e8657ad66f41`.
- Candidate remains `context_p10_r0`, penalty 10, radius 0.
- Exact published CSV SHA256:
  `2fa5c020221e49eb793cd6d59baa39e7f59e3e6a9bb0ed5a329d5331c8067824`.
- Run the unmodified official validator on that file.
- Run the unmodified official scorer once, with 1,000 seeded bootstrap draws,
  explicitly using the distributed **public** five-minute labels and the four
  distributed baselines alongside the frozen CSV. Never open private truth.
- Official source revision:
  `f8f2629ff1e0985f81d7e59d8413678514ee1530`. Use byte-exact downloaded evaluator
  sources; the previously vendored copies differ only in line endings.
- Run locally with Python networking disabled. Keep labels, reports, counts,
  timelines, diagnostics and detailed validator output in ignored private files;
  send only execution status and integrity checks to hosted tools.

## No score-driven decision

There is no score threshold, baseline-beating gate, possession-count target,
candidate comparison, output shift, refit, threshold change, or submission veto.
The candidate and output remain fixed regardless of the public-window score.
Do not investigate labelled error boundaries or infer match-specific constants.
A numerical discrepancy alone does not identify an alignment or geometry bug.
If an independently reproducible structural bug is found, stop and record it
before any correction or further labelled scoring.

Run separate synthetic coordinate/axis and adapter checks to test coordinate
conventions without target labels. Hash the CSV before and after the local check
and require identical bytes. Revalidate the exact upload packet after document
edits; update the source manifest and freeze an annotated release tag.

## Why this check is permitted

[EVALUATION.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/EVALUATION.md)
explicitly provides public-window scoring and bootstrap commands as a worked
example, while forbidding choosing versions from that window.
[RULES.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/RULES.md)
and the FAQ limit its use to pipeline correctness, not training or tuning. The
critic's proposed baseline/possession-count acceptance gate is therefore omitted.
