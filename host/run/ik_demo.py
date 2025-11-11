# host/run/ik_demo.py
import argparse, json, math, socket, sys, time
from typing import Dict, Tuple

from host.ik.planar import ik2d, to_servo
from host.run.gait import gait_targets, ORDER  # NEW

IP_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 33334
NUM = 8

def load_json(path: str, default: dict) -> dict:
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return default

GEOM = load_json("host/config/geometry.json", {
    "link_mm": {"hip_to_knee": 28.8, "thigh": 100, "foot": 95},
    "anchors_mm": {"LF":[74,39,0],"RF":[74,-39,0],"LR":[-74,39,0],"RR":[-74,-39,0]},
    "neutral_pose": {"x": 100.0, "z": 140.0},
})
CAL  = load_json("host/config/calibration.json", {
    "reverse":[False,True,True,True,False,True,True,True],
    "offset_deg":[0]*8,
    "limits_deg":{"hip":{"min":-180,"max":180},"knee":{"min":0,"max":180}},
})

L_THIGH = float(GEOM["link_mm"]["thigh"])
L_FOOT  = float(GEOM["link_mm"]["foot"])
X0      = float(GEOM["neutral_pose"]["x"])
Z0      = float(GEOM["neutral_pose"]["z"])

REV = list(CAL.get("reverse",  [False]*8))
OFF = list(CAL.get("offset_deg",[0.0]*8))
LIM = CAL.get("limits_deg", {"hip":{"min":-180,"max":180}, "knee":{"min":0,"max":180}})
HIP_MIN, HIP_MAX = float(LIM["hip"]["min"]), float(LIM["hip"]["max"])
KNEE_MIN, KNEE_MAX = float(LIM["knee"]["min"]), float(LIM["knee"]["max"])

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def connect_with_retry(ip: str, port: int, delay: float = 0.5) -> socket.socket:
    while True:
        try:
            s = socket.create_connection((ip, port), timeout=3)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"[ik_demo] Connected to {ip}:{port}")
            return s
        except OSError:
            time.sleep(delay)

# --- helper: guard that knee stays 'above' foot (z_knee < z_foot) ----------------
def knee_above_foot(hip_deg: float, knee_deg: float) -> bool:
    hip = math.radians(hip_deg); knee = math.radians(knee_deg)
    kz = L_THIGH*math.sin(hip)
    fz = kz + L_FOOT*math.sin(hip + knee)
    return kz < fz  # +z is DOWN, so knee must be numerically smaller than foot

def ik_for_feet(feet: Dict[str, Tuple[float, float]], elbow="down") -> Dict[str, Tuple[float, float]]:
    out = {}
    for leg in ORDER:
        x, z = feet[leg]
        hip, knee = ik2d(x, z, L_THIGH, L_FOOT, elbow=elbow)
        hip, knee = clamp(hip, HIP_MIN, HIP_MAX), clamp(knee, KNEE_MIN, KNEE_MAX)

        # guard: if numerical check fails (edge cases), flip branch once
        if not knee_above_foot(hip, knee):
            hip2, knee2 = ik2d(x, z, L_THIGH, L_FOOT, elbow=("up" if elbow=="down" else "down"))
            if knee_above_foot(hip2, knee2):
                hip, knee = hip2, knee2
        out[leg] = (hip, knee)
    return out

def pack_angles(angles_by_leg: Dict[str, Tuple[float, float]]) -> bytes:
    out, idx = [], 0
    for leg in ORDER:
        hip_deg, knee_deg = angles_by_leg[leg]
        out.append(to_servo(hip_deg, reverse=REV[idx], offset=OFF[idx])); idx += 1
        out.append(to_servo(knee_deg, reverse=REV[idx], offset=OFF[idx])); idx += 1
    return bytes([max(0, min(180, int(v))) for v in out])

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default=IP_DEFAULT)
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--gait", choices=["trot","pace","walk"], default="trot")
    ap.add_argument("--hz", type=float, default=0.6)          # cycles/sec
    ap.add_argument("--stride-mm", type=float, default=60.0)  # fore-aft peak-to-peak
    ap.add_argument("--lift-mm",   type=float, default=25.0)  # foot clearance in swing
    ap.add_argument("--beta",      type=float, default=0.6)   # duty factor (stance share)
    ap.add_argument("--fps", type=float, default=50.0)
    args = ap.parse_args(argv)

    sock = connect_with_retry(args.ip, args.port)
    dt = 1.0 / max(1.0, args.fps)
    t0 = time.time()

    try:
        while True:
            t = time.time() - t0
            feet = gait_targets(t, args.hz, args.gait, X0, Z0,
                                stride=args.stride_mm,
                                lift=args.lift_mm,
                                beta=args.beta)
            angles = ik_for_feet(feet, elbow="down")
            pkt = pack_angles(angles)
            try:
                sock.sendall(pkt)
            except (BrokenPipeError, ConnectionResetError, OSError):
                try: sock.close()
                except: pass
                sock = connect_with_retry(args.ip, args.port)
                continue
            time.sleep(dt)
    finally:
        try: sock.close()
        except: pass

if __name__ == "__main__":
    sys.exit(main())
