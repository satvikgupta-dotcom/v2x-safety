import streamlit as st, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from risk_engine import assess, CASES
import simulator

st.set_page_config(page_title="V2X Overtake Risk Engine", layout="wide")
st.title("Connected Vehicle Safety System")
st.caption("Driving intent sharing using V2V communication | Satvik Gupta | Project 2627S761 | MIT-WPU Pune | Academic simulation, not DSRC or C-V2X")

tab1, tab2, tab3 = st.tabs(["1. Live risk engine", "2. Scenario simulation (130 s)", "3. Rule tests"])

# ---------------- tab 1
with tab1:
    st.write("V2 asks to overtake the car ahead. Change the road situation and read the advice.")
    c1, c2 = st.columns(2)
    with c1:
        g = st.slider("Gap to car ahead (m)", 2, 60, 20)
        v_f = st.slider("Speed of car ahead (m/s)", 0, 23, 12)
        v2 = st.slider("Speed V2 wants to drive (m/s)", 0, 30, 20)
        braking = st.checkbox("Car ahead is braking")
    with c2:
        onc = st.checkbox("Oncoming vehicle present", value=True)
        d_o = st.slider("Oncoming distance (m)", 50, 600, 300, disabled=not onc)
        v_o = st.slider("Oncoming speed (m/s)", 0, 30, 14, disabled=not onc)
        sig = st.checkbox("Signal green in range", value=True)
        ped = st.checkbox("Pedestrian within 260 m")
    score, verdict, reasons, margin = assess(g, v_f, v2, d_o if onc else None, v_o, braking, sig, ped)
    {"SAFE": st.success, "HIGH RISK": st.warning, "DO NOT OVERTAKE": st.error}[verdict](f"{verdict}   (score {score})")
    if margin is not None: st.write(f"Oncoming time margin: **{margin:.2f} s**")
    st.write("Rules fired:" if reasons else "No rule fired.")
    for r in reasons: st.write("- " + r)

# ---------------- tab 2
@st.cache_data
def get_run():
    return simulator.run()
frames, msgs, decisions = get_run()
df = pd.DataFrame(frames)

with tab2:
    st.write("Scheduled scenario: V2 asks to overtake at 8, 26 and 36 s; V1 brakes at 14 s; a pedestrian crosses at 50 and 104 s; an ambulance comes at 80 s.")
    t = st.slider("Time (s)", 0.0, float(df.t.max()), 36.0, step=0.5)
    row = df.iloc[(df.t - t).abs().argmin()]
    fig, ax = plt.subplots(figsize=(10, 2.6))
    ax.axhspan(100, 246, color="#3a434b"); ax.set_xlim(0, 1000); ax.set_ylim(260, 90); ax.axis("off")
    ax.plot([0, 1000], [173, 173], "--", color="#e8e2c4", lw=1)
    ax.axvline(640, color="#999", lw=14, alpha=.5); ax.text(640, 88, "Junction (signal)", ha="center", fontsize=8)
    ax.plot([626, 626], [102, 172], color="#e8e2c4", lw=2)
    ax.plot([300, 300], [104, 244], ":", color="#e8e2c4", lw=5); ax.text(300, 258, "Crossing", ha="center", fontsize=8, color="k")
    for cid in ["V1", "V3"]: ax.plot(row[cid], 132, "s", color="#9fb3c4", ms=11); ax.text(row[cid], 120, cid, ha="center", fontsize=8, color="w")
    ax.plot(row["V2"], 132 if row["V2_lane"] == "E" else 214, "s", color="#4cc3e6", ms=11); ax.text(row["V2"], 120 if row["V2_lane"] == "E" else 202, "V2", ha="center", fontsize=8, color="w")
    for x in row["onc"]: ax.plot(x, 214, "s", color="#9fb3c4", ms=11)
    if row["amb"] is not None and row["amb"] == row["amb"]: ax.plot(row["amb"], 132, "s", color="#d93025", ms=11); ax.text(row["amb"], 120, "AMB", ha="center", fontsize=8, color="w")
    if row["ped"]: ax.plot(300, 150, "o", color="#ee79b8", ms=9)
    col = {"G": "#38d26b", "Y": "#ffc233", "R": "#ff4d42"}[row["ew"]]
    ax.plot(612, 96, "o", color=col, ms=10)
    st.pyplot(fig, clear_figure=True)
    st.write(f"t = {row['t']:.1f} s | E-W signal: {row['ew']} | live risk for V2: **{row['verdict']}**" + (f" (score {int(row['score'])})" if row["score"] == row["score"] and row["score"] is not None else ""))

    st.subheader("Overtake decisions")
    st.dataframe(pd.DataFrame([{"Time (s)": d["t"], "Front car": d["front"], "Gap (m)": round(d["gap"]), "Verdict": d["verdict"],
                                "Score": d["score"], "Rules fired": "; ".join(d["reasons"]) or "none"} for d in decisions]), hide_index=True, width="stretch")
    m = pd.DataFrame(msgs, columns=["Time (s)", "Type", "Message"])
    a, b = st.columns([1, 2])
    with a:
        st.subheader("Messages by type")
        st.bar_chart(m[m.Type != "SYS"].Type.value_counts())
        st.write(f"Total V2X messages: **{(m.Type != 'SYS').sum()}**")
    with b:
        st.subheader("Message log")
        st.dataframe(m, hide_index=True, width="stretch", height=300)
    st.subheader("Live risk score over time")
    st.line_chart(df.set_index("t")["score"])
    st.caption("Gaps in the line mean no car was within 150 m ahead of V2.")

# ---------------- tab 3
with tab3:
    rows = []
    for name, kw, es, ev in CASES:
        s, v, why, _ = assess(**kw)
        rows.append({"Test": name, "Expected": f"{es} {ev}", "Got": f"{s} {v}", "Result": "PASS" if (s == es and v == ev) else "FAIL"})
    t_df = pd.DataFrame(rows)
    st.write(f"**{(t_df.Result == 'PASS').sum()} of {len(t_df)} tests passed.** Expected values were hand-calculated from the rule table (Table 4.1).")
    st.dataframe(t_df, hide_index=True, width="stretch")

st.caption("Thresholds are engineering assumptions, not validated. The simulation is an academic model.")
