# sweep.py — sweep one index 0..7 while others stay at 90
import socket, time, math, argparse

IP, PORT = "127.0.0.1", 33334
NUM = 8

def main():
    p = argparse.ArgumentParser()
    p.add_argument("index", type=int, help="servo index 0..7")
    p.add_argument("--center", type=int, default=90)
    p.add_argument("--amp", type=int, default=25)
    p.add_argument("--hz", type=float, default=0.5)  # 0.5 Hz = 2 s per cycle
    a = p.parse_args()

    s = socket.create_connection((IP, PORT))
    packet = [a.center] * NUM
    t0 = time.time()
    try:
        while True:
            x = math.sin(2 * math.pi * (time.time() - t0) * a.hz)
            val = int(round(a.center + a.amp * x))
            val = max(0, min(180, val))
            packet[a.index] = val
            s.sendall(bytes(packet))
            time.sleep(0.02)
    finally:
        s.close()

if __name__ == "__main__":
    main()
