# host/run/ik_demo.py
import socket, time, math, json
from host.ik.planar import ik2d, to_servo

IP, PORT, NUM = "127.0.0.1", 33334, 8
ORDER = ["LF","RF","LR","RR"]  # (hip,knee) per leg

def load(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception:
        return default

geom = load("host/config/geometry.json", {
    "link_mm": {"thigh": 84, "foot": 127},
    "anchors_mm": {"LF":[74,39,0],"RF":[74,-39,0],"LR":[-74,39,0],"RR":[-74,-39,0]},
    "neutral_pose":{"x":90,"z":120}
})
cal = load("host/config/calibration.json", {
    "reverse":[False,True,True,True,False,True,True,True],
    "offset_deg":[0,0,0,0,0,0,0,0]
})

REV = cal["reverse"]; OFF = cal["offset_deg"]
L_THIGH = geom["link_mm"]["thigh"]; L_FOOT = geom["link_mm"]["foot"]
X0 = geom["neutral_pose"]["x"];     Z0     = geom["neutral_pose"]["z"]

def pack(angles_by_leg):
    out=[]; idx=0
    for leg in ORDER:
        hip,knee = angles_by_leg[leg]
        out.append(to_servo(hip,  reverse=REV[idx], offset=OFF[idx])); idx+=1
        out.append(to_servo(knee, reverse=REV[idx], offset=OFF[idx])); idx+=1
    return out  # length 8

def connect_with_retry(ip, port, delay=0.5):
    while True:
        try:
            s = socket.create_connection((ip, port), timeout=3)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"Connected to {ip}:{port}")
            return s
        except OSError:
            time.sleep(delay)

if __name__ == "__main__":
    sock = connect_with_retry(IP, PORT)
    t0 = time.time()
    try:
        while True:
            t = time.time() - t0
            z = Z0 + 15.0*(0.5 - 0.5*math.cos(2*math.pi*t*0.5))
            x_lf = X0 + 10.0*math.sin(2*math.pi*t*0.5)
            x_oth= X0
            ang = {
              "LF": ik2d(x_lf, z, L_THIGH, L_FOOT),
              "RF": ik2d(x_oth, z, L_THIGH, L_FOOT),
              "LR": ik2d(x_oth, z, L_THIGH, L_FOOT),
              "RR": ik2d(x_oth, z, L_THIGH, L_FOOT),
            }
            packet = pack(ang)
            try:
                sock.sendall(bytes(packet))
            except (BrokenPipeError, ConnectionResetError, OSError):
                try: sock.close()
                except: pass
                sock = connect_with_retry(IP, PORT)
                continue
            time.sleep(0.02)
    finally:
        try: sock.close()
        except: pass
