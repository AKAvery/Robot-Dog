# host/sim/server_view.py
import socket, threading, math, queue
import matplotlib
matplotlib.use("MacOSX")  # explicit on macOS
import matplotlib.pyplot as plt

DISCOVERY_PORT, CONTROL_PORT = 33333, 33334
SECRET = b"change-me"
NUM = 8
ORDER = ["LF","RF","LR","RR"]
ANCH = {"LF":(+90,+60), "RF":(+90,-60), "LR":(-90,+60), "RR":(-90,-60)}
L_THIGH, L_FOOT = 84.0, 127.0

import json, os
def _load_cal():
    try:
        with open("host/config/calibration.json","r") as f: return json.load(f)
    except Exception: return {"reverse":[False]*8, "offset_deg":[0]*8}

CAL = _load_cal()

def decode(packet):
    it = iter(packet); vals={}
    idx = 0
    for leg in ORDER:
        hip_b = next(it); knee_b = next(it)
        hip  = hip_b  - 90
        knee = knee_b - 90
        # apply reverse and offsets to reconstruct logical angles
        if CAL["reverse"][idx]:   hip  = -hip
        hip  = hip  - CAL["offset_deg"][idx]; idx+=1
        if CAL["reverse"][idx]:   knee = -knee
        knee = knee - CAL["offset_deg"][idx]; idx+=1
        vals[leg] = (math.radians(hip), math.radians(knee))
    return vals


def fk(ax, ay, hip, knee):
    x1 = ax + L_THIGH*math.cos(hip); z1 = 0 - L_THIGH*math.sin(hip)
    x2 = x1 + L_FOOT*math.cos(hip+knee); z2 = z1 - L_FOOT*math.sin(hip+knee)
    return (ax,0),(x1,z1),(x2,z2)

def discovery():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except OSError: pass
    s.bind(("", DISCOVERY_PORT))
    while True:
        d, a = s.recvfrom(1024)
        if d == SECRET: s.sendto(SECRET, a)

def control(pktq):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", CONTROL_PORT)); srv.listen(1)
    print(f"Listening on TCP {CONTROL_PORT}")
    while True:
        c, addr = srv.accept(); print("Client:", addr)
        try:
            while True:
                buf=b""
                while len(buf) < NUM:
                    chunk=c.recv(NUM-len(buf))
                    if not chunk: raise ConnectionResetError
                    buf+=chunk
                # keep only the latest
                while not pktq.empty():
                    try: pktq.get_nowait()
                    except queue.Empty: break
                pktq.put_nowait(list(buf))
        except Exception:
            print("Client disconnected")
        finally:
            try: c.close()
            except: pass

if __name__ == "__main__":
    pktq = queue.Queue(maxsize=1)

    # start network threads
    threading.Thread(target=discovery, daemon=True).start()
    threading.Thread(target=control, args=(pktq,), daemon=True).start()

    # set up plot on main thread
    fig, ax = plt.subplots()
    ax.set_aspect('equal'); ax.set_xlim(-220,220); ax.set_ylim(-220,120); ax.invert_yaxis()
    lines = {leg: ax.plot([], [], marker='o')[0] for leg in ORDER}
    ax.set_title("Quad 2-DOF stick viewer")

    def on_timer():
        try:
            pkt = pktq.get_nowait()
        except queue.Empty:
            return
        vals = decode(pkt)
        for leg in ORDER:
            (hx,hz),(kx,kz),(fx,fz) = fk(*ANCH[leg], *vals[leg])
            lines[leg].set_data([hx,kx,fx], [hz,kz,fz])
        fig.canvas.draw_idle()

    # 50 Hz refresh timer on the main thread
    timer = fig.canvas.new_timer(interval=20)
    timer.add_callback(on_timer)
    timer.start()
    plt.show()
