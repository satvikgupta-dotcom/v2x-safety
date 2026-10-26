"""
Overtake risk engine + test suite (standalone, no installs needed: Python 3 only).
Rules are the ones in Table 4.1 of the report. Run:  python3 risk_engine.py
"""
import csv

V_OT = 24.0  # assumed overtaking speed (m/s)

def assess(g, v_f, v2, d_o=None, v_o=0.0, front_braking=False,
           signal_green_in_range=True, ped_within_260=False,
           safe_lt=30, high_lt=60):
    """Return (score, verdict, reasons). g=gap to car ahead (m), v_f=its speed,
    v2=ego speed, d_o/v_o=nearest oncoming car distance (m)/speed (m/s)."""
    score, hard, reasons = 0, False, []

    # soft rule: gap
    if g < 8:    score += 30; reasons.append("gap < 8 m (+30)")
    elif g < 15: score += 10; reasons.append("gap < 15 m (+10)")
    # soft rule: speed advantage
    if v2 - v_f < 3: score += 15; reasons.append("speed advantage < 3 m/s (+15)")
    # oncoming time margin
    margin = None
    if d_o is not None and V_OT > v_f:
        t_pass = (g + 30) / (V_OT - v_f)
        t_onc = d_o / (V_OT + v_o)
        margin = t_onc - t_pass
        if margin < 0:   score += 60; hard = True; reasons.append(f"HARD: oncoming margin {margin:.2f} s < 0 (+60)")
        elif margin < 3: score += 35; reasons.append(f"oncoming margin {margin:.2f} s < 3 s (+35)")
        elif margin < 6: score += 15; reasons.append(f"oncoming margin {margin:.2f} s < 6 s (+15)")
    # hard rules
    if front_braking:
        score += 50; hard = True; reasons.append("HARD: car ahead braking (+50)")
    if not signal_green_in_range:
        score += 50; hard = True; reasons.append("HARD: signal not green within g+170 m (+50)")
    if ped_within_260:
        score += 60; hard = True; reasons.append("HARD: pedestrian within 260 m (+60)")

    if hard or score >= high_lt: verdict = "DO NOT OVERTAKE"
    elif score >= safe_lt:       verdict = "HIGH RISK"
    else:                        verdict = "SAFE"
    return score, verdict, reasons, margin

# (name, inputs, expected score, expected verdict) -- expected values hand-calculated from Table 4.1
CASES = [
 ("T1 Clear road",              dict(g=25, v_f=12, v2=20),                                   0,  "SAFE"),
 ("T2 Report worked example",   dict(g=20, v_f=12, v2=20, d_o=300, v_o=14),                  15, "SAFE"),
 ("T3 Example + low speed adv", dict(g=20, v_f=12, v2=14, d_o=300, v_o=14),                  30, "HIGH RISK"),
 ("T4 Gap 6 m",                 dict(g=6,  v_f=12, v2=20),                                   30, "HIGH RISK"),
 ("T5 Gap 10 m",                dict(g=10, v_f=12, v2=20),                                   10, "SAFE"),
 ("T6 Gap exactly 8 m",         dict(g=8,  v_f=12, v2=20),                                   10, "SAFE"),
 ("T7 Gap exactly 15 m",        dict(g=15, v_f=12, v2=20),                                   0,  "SAFE"),
 ("T8 Speed adv exactly 3",     dict(g=25, v_f=12, v2=15),                                   0,  "SAFE"),
 ("T9 Front car braking",       dict(g=25, v_f=12, v2=20, front_braking=True),               50, "DO NOT OVERTAKE"),
 ("T10 Oncoming too close",     dict(g=20, v_f=12, v2=20, d_o=150, v_o=14),                  60, "DO NOT OVERTAKE"),
 ("T11 Margin 1.5 s (soft)",    dict(g=20, v_f=12, v2=20, d_o=215, v_o=14),                  35, "HIGH RISK"),
 ("T12 Signal not green",       dict(g=25, v_f=12, v2=20, signal_green_in_range=False),      50, "DO NOT OVERTAKE"),
 ("T13 Pedestrian near",        dict(g=25, v_f=12, v2=20, ped_within_260=True),              60, "DO NOT OVERTAKE"),
 ("T14 Soft rules add to 65",   dict(g=6,  v_f=12, v2=20, d_o=171, v_o=14),                  65, "DO NOT OVERTAKE"),
 ("T15 Oncoming + red (24 s)",  dict(g=20, v_f=12, v2=20, d_o=150, v_o=14, signal_green_in_range=False), 110, "DO NOT OVERTAKE"),
]

def main():
    print(f"{'Test':30} {'Exp':>4} {'Got':>4}  {'Verdict':16} Result")
    rows, ok = [], 0
    for name, kw, exp_s, exp_v in CASES:
        s, v, why, m = assess(**kw)
        passed = (s == exp_s and v == exp_v); ok += passed
        print(f"{name:30} {exp_s:>4} {s:>4}  {v:16} {'PASS' if passed else 'FAIL'}")
        rows.append([name, exp_s, s, exp_v, v, "PASS" if passed else "FAIL", "; ".join(why)])
    print(f"\n{ok}/{len(CASES)} tests passed")
    with open("test_results.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Test","Expected score","Got score","Expected verdict","Got verdict","Result","Rules fired"]); w.writerows(rows)

    # sensitivity: move the SAFE/HIGH-RISK threshold from 30 to 40 and see which verdicts change
    print("\nSensitivity: SAFE threshold 30 -> 40")
    changed = 0
    for name, kw, _, _ in CASES:
        v30 = assess(**kw)[1]; v40 = assess(**kw, safe_lt=40)[1]
        if v30 != v40: changed += 1; print(f"  {name}: {v30} -> {v40}")
    print(f"  {changed} of {len(CASES)} verdicts changed")

if __name__ == "__main__":
    main()
