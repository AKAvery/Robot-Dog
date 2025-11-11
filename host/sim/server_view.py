# host/sim/server_view.py
# 2-DOF stick viewer that decodes 8 servo bytes (hip, knee per leg),
# applies calibration.json (reverse/offset), and renders legs in the x–z plane.
# Conventions:
#   +x = forward; +z = down (plot uses invert_yaxis so down is visually downward)

import argparse
import json
import math
import os
import queue
import socket
import threading

# --- Matplotlib backend (macOS first, fallback to Tk) -------------------------
import matplotlib
try:
    matplotlib.use("MacOSX")
except Exception:
    matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

DISCOVERY_PORT = 33333
CONTROL_PORT   = 33334
SECRET = b"change-me"
NUM = 8
ORDER = ["LF", "RF", "LR", "RR"]  # packet order: (hip, knee) per leg

# ------------------------------ config loaders --------------------------------

def _load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def load_geometry():
    # Defaults are sensible, but we prefer your repo files.
    g_default = {
        "link_mm": {"hip_to_knee": 28.8, "thigh": 100.0, "foot": 95.0},
        "anchors_mm": {"LF":[74, 39, 0], "RF":[74, -39, 0], "LR":[-74, 39, 0], "RR":[-74, -39, 0]},
        "neutral_pose": {"x": 100.0, "z": 140.0},
    }
    geo = _load_json("host/config/geometry.json", g_default)
    link = geo.get("link_mm", {})
    anchors_mm = geo.get("anchors_mm", {})
    L_THIGH = float(link.get("thigh", g_default["link_mm"]["thigh"]))
    L_FOOT  = float(link.get("foot",  g_default["link_mm"]["foot"]))
    # Return anchors as dict leg -> (x, z_for_view)  (we'll fill z later using --body-z)
    anchors_x = {leg: float((anchors_mm.get(leg) or [0,0,0])[0]) for leg in ORDER}
    return L_THIGH, L_FOOT, anchors_x

def load_calibration():
    c_default = {"reverse": [False]*8, "offset_deg": [0.0]*8}
    cal = _load_json("host/config/calibration.json", c_default)
    rev = list(cal.get("reverse", c_default["reverse"]))
    off = list(cal.get("offset_deg", c_default["offset_deg"]))
    if len(rev) < NUM: rev = (rev + [False]*NUM)[:NUM]
    if len(off) < NUM: off = (off + [0.0]*NUM)[:NUM]
    return rev, off

REV, OFF = load_calibration()
L_THIGH, L_FOOT, ANCHORS_X = load_geometry()

# ----------------------------- packet decoding --------------------------------

def decode(packet):
    """
    Map 8 servo bytes (0..180) back to logical angles (hip, knee) in radians,
    undoing per-channel reverse and offsets. Positive angles bend the leg DOWN.
    """
    it = iter(packet)
    vals = {}
    idx = 0
    for leg in ORDER:
        hip_b  = next(it)   # 0..180
        knee_b = next(it)   # 0..180
        hip  = hip_b  - 90.0
        knee = knee_b - 90.0
        if REV[idx]: hip  = -hip
        hip  = hip  - OFF[idx]; idx += 1
        if REV[idx]: knee = -knee
        knee = knee - OFF[idx]; idx += 1
        vals[leg] = (math.radians(hip), math.radians(knee))
    return vals

# --------------------------- forward kinematics --------------------------------

def fk(ax, az, hip, knee):
    """
    Forward kinematics for a 2-DOF planar leg in x–z:
      hip at (ax, az)
      knee at (ax + L1 cos(hip), az + L1 sin(hip))
      foot at knee + (L2 cos(hip+knee), L2 sin(hip+knee))
    Positive angles bend DOWN (increasing z).  This matches our IK/servo mapping.
    """
    x1 = ax + L_THIGH * math.cos(hip)
    z1 = az + L_THIGH * math.sin(hip)
    x2 = x1 + L_FOOT  * math.cos(hip + knee)
    z2 = z1 + L_FOOT  * math.sin(hip + knee)
    return (ax, az), (x1, z1), (x2, z2)

# ------------------------------ networking ------------------------------------

def discovery():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except OSError: pass
    s.bind(("", DISCOVERY_PORT))
    while True:
        data, addr = s.recvfrom(1024)
        if data == SECRET:
            s.sendto(SECRET, addr)

def control(port, pktq):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port)); srv.listen(1)
    print(f"[server_view] Listening on TCP {port}")
    while True:
        c, addr = srv.accept()
        print("[server_view] Client:", addr)
        try:
            while True:
                buf = b""
                while len(buf) < NUM:
                    chunk = c.recv(NUM - len(buf))
                    if not chunk:
                        raise ConnectionResetError
                    buf += chunk
                # keep only newest packet
                while not pktq.empty():
                    try: pktq.get_nowait()
                    except queue.Empty: break
                pktq.put_nowait(list(buf))
        except Exception:
            print("[server_view] Client disconnected")
        finally:
            try: c.close()
            except: pass

# ---------------------------------- main ---------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Quad 2-DOF stick viewer")
    ap.add_argument("--port", type=int, default=CONTROL_PORT)
    ap.add_argument("--fps",  type=float, default=50.0)
    ap.add_argument("--body-z", type=float, default=-60.0,
                    help="hip height (z of all anchors, negative draws higher)")
    ap.add_argument("--xlim", type=float, nargs=2, default=None, metavar=("XMIN","XMAX"))
    ap.add_argument("--ylim", type=float, nargs=2, default=None, metavar=("YMIN","YMAX"),
                    help="Y axis is z; use negative to move hips toward top. Plot is inverted.")
    args = ap.parse_args()

    # Build anchor map: take X from geometry.json, set Z from --body-z
    ANCH = {leg: (ANCHORS_X.get(leg, 0.0), float(args.body_z)) for leg in ORDER}

    pktq = queue.Queue(maxsize=1)
    threading.Thread(target=discovery, daemon=True).start()
    threading.Thread(target=control, args=(args.port, pktq), daemon=True).start()

    # Auto axes from geometry
    reach = L_THIGH + L_FOOT + 20.0
    xs = [ANCH[l][0] for l in ORDER]
    xmin = min(xs) - reach
    xmax = max(xs) + reach
    # default z (remember: invert_yaxis -> larger z is lower on screen)
    ymin = args.body_z - 40.0     # little headroom above hips
    ymax = args.body_z + reach    # room below for legs

    fig, ax = plt.subplots()
    ax.set_aspect("equal")
    ax.set_xlim(*(args.xlim if args.xlim else (xmin, xmax)))
    ax.set_ylim(*(args.ylim if args.ylim else (ymin, ymax)))
    ax.invert_yaxis()  # +z is down

    # draw a simple "body" line through hip anchors
    body_x = [ANCH["LR"][0], ANCH["RR"][0], ANCH["RF"][0], ANCH["LF"][0]]
    body_z = [args.body_z]*4
    ax.plot([ANCH["LR"][0], ANCH["RR"][0]], [args.body_z, args.body_z], lw=2, alpha=0.4, color="gray")
    ax.plot([ANCH["LF"][0], ANCH["RF"][0]], [args.body_z, args.body_z], lw=2, alpha=0.4, color="gray")

    # one polyline per leg (hip -> knee -> foot)
    lines = {leg: ax.plot([], [], marker="o")[0] for leg in ORDER}
    ax.set_title("Quad 2-DOF stick viewer")

    # single-use print of decoded logical angles to sanity-check
    printed_once = {"done": False}

    def on_timer():
        try:
            pkt = pktq.get_nowait()
        except queue.Empty:
            return

        vals = decode(pkt)
        if not printed_once["done"]:
            # Print one frame of logical angles in degrees for quick verification
            dbg = {leg: tuple(round(math.degrees(a), 1) for a in vals[leg]) for leg in ORDER}
            print("[server_view] logical angles (deg):", dbg)
            printed_once["done"] = True

        for leg in ORDER:
            (hx, hz), (kx, kz), (fx, fz) = fk(*ANCH[leg], *vals[leg])
            lines[leg].set_data([hx, kx, fx], [hz, kz, fz])
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=max(5, int(1000.0/args.fps)))
    timer.add_callback(on_timer)
    timer.start()
    plt.show()

if __name__ == "__main__":
    main()
