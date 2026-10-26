"""
Simple V2X road simulator (Python port of the browser version).
Cars V1, V2 (ego), V3 drive east on the left lane; oncoming cars drive west.
One signal at x=640 m, a pedestrian crossing at x=300 m, an ambulance on request.
Every event creates a V2V / V2I / V2P / V2N message. V2 asks to overtake and the
rule-based risk engine in risk_engine.py decides.
"""
from risk_engine import assess

DT, CAR_L, V_OT, GAP_T = 0.1, 5.0, 24.0, 20.0
SIGX, STOPX, PEDX = 640.0, 626.0, 300.0

def ew_phase(t):
    c = t % 30
    return "G" if c < 14 else ("Y" if c < 17 else "R")

class Car:
    def __init__(self, cid, x, desired):
        self.id, self.x, self.v, self.a, self.desired = cid, x, 12.0, 0.0, desired
        self.lane, self.braking = "E", False

class World:
    def __init__(self):
        self.t = 0.0
        self.cars = [Car("V1", 250, 12), Car("V2", 195, 20), Car("V3", 130, 14)]
        self.onc = [[620.0, 14.0]]            # [x, speed]
        self.next_onc = 22.0
        self.amb = None                        # [x, speed]
        self.alerted = set()
        self.ped_until = -1.0
        self.v1_brake_until = -1.0
        self.mode, self.target = "follow", None
        self.last_ew = None
        self.msgs, self.decisions = [], []

    # ---- helpers
    @property
    def v2(self): return self.cars[1]
    @property
    def ped_active(self): return self.t < self.ped_until
    def msg(self, kind, text): self.msgs.append((round(self.t, 1), kind, text))

    def front_of(self, c):
        best = None
        for o in self.cars:
            if o is c or o.lane != c.lane or o.x <= c.x: continue
            if c.id == "V2" and self.mode == "pass" and o is self.target: continue
            if best is None or o.x < best.x: best = o
        return best

    def target_speed(self, c):
        tv = c.desired
        if self.amb and self.amb[0] < c.x and c.x - self.amb[0] < 180: tv *= 0.5
        f = self.front_of(c)
        if f:
            g = f.x - c.x - CAR_L
            tv = min(tv, max(0.0, f.v + 0.5 * (g - GAP_T)))
        if not (c.id == "V2" and self.mode == "pass"):
            if ew_phase(self.t) != "G":
                d = STOPX - c.x
                if -2 < d < c.v ** 2 / 6 + 45: tv = min(tv, max(0.0, 0.35 * (d - 4)))
            if self.ped_active:
                d = PEDX - 8 - c.x
                if -2 < d < c.v ** 2 / 6 + 45: tv = min(tv, max(0.0, 0.35 * (d - 2)))
        if c.id == "V1" and self.t < self.v1_brake_until: tv = 0.0
        return tv

    # ---- events
    def brake_v1(self):
        self.v1_brake_until = self.t + 4; self.msg("V2V", "V1 -> all: HARD_BRAKE")
    def pedestrian(self):
        if not self.ped_active:
            self.ped_until = self.t + 10; self.msg("V2P", "PED -> cars: PEDESTRIAN_AT_CROSSING (x=300 m)")
    def ambulance(self):
        if not self.amb:
            self.amb = [-30.0, 30.0]; self.alerted = set()
            self.msg("V2N", "CLOUD -> V1, V2, V3: AMBULANCE_ALERT")

    def evaluate(self):
        v2 = self.v2; f = self.front_of(v2)
        if self.mode != "follow" or f is None or f.x - v2.x - CAR_L > 150: return None
        g = f.x - v2.x - CAR_L
        ahead = [o for o in self.onc if o[0] > v2.x]
        on = min(ahead, key=lambda o: o[0]) if ahead else None
        sig_ahead = v2.x <= SIGX <= v2.x + g + 170
        res = assess(g=g, v_f=f.v, v2=v2.desired,
                     d_o=(on[0] - v2.x) if on else None, v_o=on[1] if on else 0.0,
                     front_braking=f.braking or (f.id == "V1" and self.t < self.v1_brake_until),
                     signal_green_in_range=not (sig_ahead and ew_phase(self.t) != "G"),
                     ped_within_260=self.ped_active and v2.x <= PEDX <= v2.x + 260)
        return dict(score=res[0], verdict=res[1], reasons=res[2], margin=res[3], gap=g, front=f.id)

    def request(self):
        r = self.evaluate()
        if r is None:
            self.msg("SYS", "No car within 150 m ahead of V2, nothing to overtake"); return None
        self.msg("V2V", f"V2 -> nearby cars: OVERTAKE_INTENT of {r['front']} (gap {r['gap']:.0f} m)")
        r["t"] = round(self.t, 1)
        if r["verdict"] == "SAFE":
            self.mode, self.target = "pass", self.front_of(self.v2)
            self.v2.lane, self.v2.desired = "W", 24.0
            self.msg("SYS", f"Advice SAFE (score {r['score']}). V2 overtakes {r['front']}")
        else:
            self.msg("SYS", f"Advice {r['verdict']} (score {r['score']}). Refused: " + "; ".join(r["reasons"]))
        self.decisions.append(r); return r

    # ---- one time step
    def step(self):
        self.t = round(self.t + DT, 1)
        ew = ew_phase(self.t)
        if ew != self.last_ew:
            if self.last_ew is not None:
                self.msg("V2I", "RSU -> all cars: E-W signal is now " + {"G": "GREEN", "Y": "YELLOW", "R": "RED"}[ew])
            self.last_ew = ew
        if abs(self.t - self.ped_until) < 1e-6:
            self.msg("V2P", "Crossing clear: pedestrian has crossed")
        if self.t >= self.next_onc:
            self.onc.append([1050.0, 13.0]); self.next_onc += 24
        for c in self.cars:
            tv = self.target_speed(c)
            lim = 6 if (c.id == "V1" and self.t < self.v1_brake_until) else 3
            acc = tv - c.v
            if c.id == "V2" and self.mode == "pass": acc = min(acc, 3)
            acc = max(-lim * 2, min(acc * 2, 2.2)); acc = max(acc, -lim)
            c.a = acc; c.v = max(0.0, c.v + acc * DT); c.x += c.v * DT
            c.braking = c.a < -1.5
            if c.x > 1060: c.x -= 1120
        v2 = self.v2
        if self.mode == "pass":
            t = self.target
            if t is None or v2.x > t.x + CAR_L + 22 or t.x < v2.x - 50:
                self.mode, v2.lane, v2.desired = "return", "E", 20.0
                self.msg("SYS", "V2 returns to its lane")
        elif self.mode == "return":
            self.mode = "follow"
        for o in self.onc: o[0] -= o[1] * DT
        self.onc = [o for o in self.onc if o[0] > -60]
        if self.amb:
            self.amb[0] += self.amb[1] * DT
            for c in self.cars:
                if c.id not in self.alerted and self.amb[0] < c.x and c.x - self.amb[0] < 180:
                    self.alerted.add(c.id)
                    self.msg("V2V", f"AMB -> {c.id}: emergency vehicle approaching, give way")
            if self.amb[0] > 1080: self.amb = None

AUTO = [(8, "req"), (14, "brake"), (26, "req"), (36, "req"), (50, "ped"), (80, "amb"), (104, "ped")]

def run(duration=130.0, auto=True):
    """Run the scheduled scenario. Returns (frames, messages, decisions)."""
    w, frames, i = World(), [], 0
    for n in range(int(duration / DT)):
        w.step()
        while auto and i < len(AUTO) and w.t >= AUTO[i][0]:
            a = AUTO[i][1]; i += 1
            {"req": w.request, "brake": w.brake_v1, "ped": w.pedestrian, "amb": w.ambulance}[a]()
        if n % 5 == 0:
            ev = w.evaluate()
            frames.append(dict(t=w.t, **{c.id: c.x for c in w.cars}, V2_lane=w.v2.lane,
                               onc=[o[0] for o in w.onc], amb=w.amb[0] if w.amb else None,
                               ped=w.ped_active, ew=ew_phase(w.t),
                               score=ev["score"] if ev else None, verdict=ev["verdict"] if ev else "-"))
    return frames, w.msgs, w.decisions
