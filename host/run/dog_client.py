# src/dog.py
import socket, time

DISCOVERY_PORT = 33333
CONTROL_PORT   = 33334
SECRET         = b"change-me"
NUM_SERVOS     = 8  # switch to 12 when you wire all joints

def discover():
    # Send one broadcast and wait for the echo from server.py
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.bind(("", 0))                 # <-- EPHEMERAL local port (fixes your error)
    udp.settimeout(3.0)
    udp.sendto(SECRET, ("255.255.255.255", DISCOVERY_PORT))
    data, (ip, _port) = udp.recvfrom(1024)
    udp.close()
    if data != SECRET:
        raise RuntimeError("Secret mismatch")
    return ip

def connect(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, CONTROL_PORT))
    return s

def clamp01(x): return max(0, min(180, int(x)))

if __name__ == "__main__":
    # If broadcast is flaky on your network, skip discovery: ip = "127.0.0.1"
    ip = discover()
    print("Discovered simulator at", ip)
    sock = connect(ip)
    print("Connected")

    # send a steady neutral pose; change these to test
    packet = [90] * NUM_SERVOS        # values must be 0..180
    try:
        while True:
            sock.sendall(bytes(packet))   # server.py expects exactly NUM_SERVOS bytes
            time.sleep(0.02)              # ~50 Hz
    finally:
        sock.close()
