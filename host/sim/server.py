# host/sim/server.py
import socket, threading

DISCOVERY_PORT = 33333
CONTROL_PORT   = 33334
SECRET = b"change-me"
NUM = 8  # bump to 12 later

def discovery():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", DISCOVERY_PORT))
    while True:
        data, addr = s.recvfrom(1024)
        if data == SECRET:
            s.sendto(SECRET, addr)

def control():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", CONTROL_PORT))
    srv.listen(1)
    print(f"Listening on TCP {CONTROL_PORT}")
    while True:
        c, addr = srv.accept()
        print("Client:", addr)
        try:
            while True:
                buf = b""
                while len(buf) < NUM:
                    chunk = c.recv(NUM - len(buf))
                    if not chunk:
                        raise ConnectionResetError
                    buf += chunk
                print(list(buf))
        except Exception:
            print("Client disconnected")
        finally:
            try: c.close()
            except: pass

if __name__ == "__main__":
    threading.Thread(target=discovery, daemon=True).start()
    control()
