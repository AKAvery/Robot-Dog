# host/run/ik_demo.py
# Streams 8 servo bytes (hip-pitch, knee per leg) computed via planar IK.
# Works with host/sim/server.py or server_view.py (TCP 33334).

import argparse
import json
import math
import socket
import sys
import time
from typing import Dict, Tuple

from host.ik.planar import ik2d, to_servo  # 2-DOF IK (hip-pitch + knee)

IP_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 33334
NUM = 8  # 2 DOF x 4 legs
ORDER = ["LF", "RF", "LR", "RR"]  # packet order: (hip, knee) per leg


# ----------------------------- utils -----------------------------

def load_json(path: str, default: dict) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def connect_with_retry(ip: str, port: int, delay: float = 0.5) -> socket.socket:
    while True:
        try:
            s = socket.create_connection((ip, port), timeout=3)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"[ik_demo] Connected to {ip}:{port}")
            return s
        except OSError:
            time.sleep(delay)


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


# -------------------------- configuration ------------------------

_geom_default = {
    "link_mm": {"hip_to_knee": 28, "thigh": 96, "foot": 125},
    "anchors_mm": {"LF": [74, 39, 0], "RF": [74, -39, 0], "LR": [-74, 39, 0], "RR": [-74, -39, 0]},
    "neutral_pose": {"x": 100, "z": 140}
}
_cal_default = {
    "reverse": [False, True, True, True, False, True, True, True],
    "offset_deg": [0, 0, 0, 0, 0, 0, 0, 0],
    # Optional:
    # "limits_deg": {"hip": {"min": -180, "max": 180}, "knee": {"min": 0, "max": 180}}
}

GEOM = load_json("host/config/geometry.json", _geom_default)
CAL = load_json("host/config/calibration.json", _cal_default)

L_THIGH = float(GEOM["link_mm"]["thigh"])
L_FOOT = float(GEOM["link_mm"]["foot"])
X0 = float(GEOM["neutral_pose"]["x"])
Z0 = float(GEOM["neutral_pose"]["z"])

REV = list(CAL.get("reverse", _cal_default["reverse"]))
OFF = list(CAL.get("offset_deg", _cal_default["offset_deg"]))
if len(REV) < NUM:  # pad if needed
    REV = (REV + [False] * NUM)[:NUM]
if len(OFF) < NUM:
    OFF = (OFF + [0] * NUM)[:NUM]

_limits = CAL.get("limits_deg", {"hip": {"min": -180, "max": 180}, "knee": {"min": 0, "max": 180}})
HIP_MIN, HIP_MAX = float(_limits["hip"]["min"]), float(_limits["hip"]["max"])
KNEE_MIN, KNEE_MAX = float(_limits["knee"]["min"]), float(_limits["knee"]["max"])


# ------------------------- motion generators ---------------------

def feet_targets(
    t: float,
    mode: str,
    hz: float,
    amp_x: float,
    amp_z: float,
    x0: float,
    z0: float
) -> Dict[str, Tuple[float, float]]:
    """
    Returns foot (x,z) per leg in mm relative to each hip pivot.
    Conventions: +x forward, +z down (matches geometry.json).
    """
    w = 2 * math.pi * hz

    if mode == "stand":
        return {leg: (x0, z0) for leg in ORDER}

    if mode == "squat":
        z = z0 + amp_z * (0.5 - 0.5 * math.cos(w * t))  # smooth up/down
        return {leg: (x0, z) for leg in ORDER}

    if mode == "step":
        # LF steps in x; others hold x0; all at constant height
        x_lf = x0 + amp_x * math.sin(w * t)
        return {"LF": (x_lf, z0), "RF": (x0, z0), "LR": (x0, z0), "RR": (x0, z0)}

    if mode == "trot":
        # Diagonal pairs move in opposite phase, little ellipse in x–z
        #   swing: forward + up; stance: backward + down (very simple sketch)
        def ellipse(phase_cycles: float) -> Tuple[float, float]:
            p = 2 * math.pi * (t * hz + phase_cycles)
            x = x0 + amp_x * math.sin(p)
            z = z0 + amp_z * (0.5 - 0.5 * math.cos(p))
            return x, z

        return {
            "LF": ellipse(0.0),
            "RR": ellipse(0.0),
            "RF": ellipse(0.5),
            "LR": ellipse(0.5),
        }

    # Fallback
    return {leg: (x0, z0) for leg in ORDER}


def ik_for_feet(feet: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    """Compute logical joint angles (hip_pitch, knee) in degrees for each leg."""
    out = {}
    for leg in ORDER:
        x, z = feet[leg]
        hip, knee = ik2d(x, z, L_THIGH, L_FOOT)
        # clamp to optional limits (logical angles)
        hip = clamp(hip, HIP_MIN, HIP_MAX)
        knee = clamp(knee, KNEE_MIN, KNEE_MAX)
        out[leg] = (hip, knee)
    return out


def pack_angles(angles_by_leg: Dict[str, Tuple[float, float]]) -> bytes:
    """Map logical degrees -> servo bytes [0..180] using reverse/offset per calibration."""
    out = []
    idx = 0
    for leg in ORDER:
        hip_deg, knee_deg = angles_by_leg[leg]
        out.append(to_servo(hip_deg, reverse=REV[idx], offset=OFF[idx])); idx += 1
        out.append(to_servo(knee_deg, reverse=REV[idx], offset=OFF[idx])); idx += 1
    # ensure ints and clamp just in case
    out = [max(0, min(180, int(v))) for v in out]
    if len(out) != NUM:
        raise RuntimeError(f"Packet length {len(out)} != {NUM}")
    return bytes(out)


# ----------------------------- main ------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="IK demo streamer (8-byte 2-DOF legs)")
    ap.add_argument("--ip", default=IP_DEFAULT, help="server IP (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT, help="TCP port (default 33334)")
    ap.add_argument("--mode", choices=["stand", "squat", "step", "trot"], default="trot")
    ap.add_argument("--hz", type=float, default=0.6, help="motion frequency (Hz)")
    ap.add_argument("--amp-x", type=float, default=12.0, help="step amplitude in x (mm)")
    ap.add_argument("--amp-z", type=float, default=16.0, help="lift amplitude in z (mm)")
    ap.add_argument("--fps", type=float, default=50.0, help="send rate (frames/sec)")
    args = ap.parse_args(argv)

    sock = connect_with_retry(args.ip, args.port)
    dt = 1.0 / max(1.0, args.fps)
    t0 = time.time()

    try:
        while True:
            t = time.time() - t0
            feet = feet_targets(t, args.mode, args.hz, args.amp_x, args.amp_z, X0, Z0)
            angles = ik_for_feet(feet)
            pkt = pack_angles(angles)
            try:
                sock.sendall(pkt)
            except (BrokenPipeError, ConnectionResetError, OSError):
                try:
                    sock.close()
                except Exception:
                    pass
                sock = connect_with_retry(args.ip, args.port)
                continue
            time.sleep(dt)
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
