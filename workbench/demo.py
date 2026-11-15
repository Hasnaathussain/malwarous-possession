"""Deterministic software-demo fixture. Never an accuracy benchmark."""
import math


def make_demo():
    duration = 72.0
    truth = [(0, 14, "H"), (14, 24, "A"), (24, 34, "D"), (34, 49, "H"),
             (49, 54, "X"), (54, 64, "A"), (64, 72, "D")]
    versions = {
        "v1": [(0, 16, "H"), (16, 27, "A"), (27, 34, "D"), (34, 47, "H"),
               (47, 51, "A"), (51, 54, "X"), (54, 65, "A"), (65, 72, "D")],
        "v2": [(0, 14.5, "H"), (14.5, 24.5, "A"), (24.5, 34, "D"),
               (34, 49, "H"), (49, 54, "X"), (54, 64, "A"), (64, 72, "D")],
    }
    def spells(rows):
        return [dict(start_s=a, end_s=b, state=c) for a, b, c in rows]
    samples = []
    for frame in range(721):
        t = frame / 10
        missing = 19 <= t < 21 or 49 <= t < 54
        players = []
        for team, phase in [("H", 0), ("A", 1.4)]:
            for n in range(1, 12):
                if 49 <= t < 54 and n % 3 == 0:
                    continue
                players.append(dict(id=f"{team}{n}", team=team,
                    x=52.5 + 39 * math.sin(n * 1.9 + phase + t / 23),
                    y=34 + 28 * math.cos(n * 2.4 + phase + t / 31)))
        x, y = 52.5 + 33 * math.sin(t / 9), 34 + 24 * math.cos(t / 11)
        ball = None if missing else [x, y, 0.2 + abs(math.sin(t / 2))]
        distances = {team: min(math.hypot(p["x"] - x, p["y"] - y)
                              for p in players if p["team"] == team)
                     for team in ("H", "A")}
        samples.append(dict(t=t, ball=ball, players=players,
            quality=dict(player_coverage=len(players) / 22, ball_observed=not missing),
            evidence={"home_nearest_m": None if missing else distances["H"],
                      "away_nearest_m": None if missing else distances["A"]}))
    provenance = dict(model_version="software-demo", split="synthetic / illustrative",
                      evaluator="none — no accuracy metrics computed")
    match = dict(id="demo-01", title="Synthetic sequence · 72 seconds", duration_s=duration,
        provenance=dict(fps=10, split="synthetic software demonstration"),
        pitch=dict(length_m=105, width_m=68), samples=samples, truth=spells(truth),
        evidence_series=[dict(key="home_nearest_m", label="Nearest home player", unit="m",
            description="Euclidean player-to-ball distance in this generated fixture."),
            dict(key="away_nearest_m", label="Nearest away player", unit="m",
            description="Euclidean player-to-ball distance in this generated fixture.")],
        predictions={v: dict(spells=spells(rows), provenance=provenance)
                     for v, rows in versions.items()},
        benchmarks=[dict(version=v, metric_source="synthetic_demo", spellF1=None,
            macroF1=None, runtime_s=None, provenance=provenance) for v in versions])
    return dict(schema_version="1.0", dataset=dict(id="software-demo",
        title="Local workbench demonstration", kind="synthetic_demo", split="synthetic",
        provenance="Deterministic generated positions and authored labels. Software demo only; not accuracy evidence."),
        matches=[match])
