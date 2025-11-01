import socket
import sys
import time

# Configuration
# Ports and secret, make the ports unique and 1024 < (DISCOVERY_PORT != CONTROL_PORT) < 65536
DISCOVERY_PORT = -1
CONTROL_PORT = -2
UDP_REPLY_MSG = b"some secret key" # should be the exact same as in the ESP32 client

def handle_incoming_udp(data: bytes, addr):
    ip, port = addr[0], addr[1]
    print(f"[+] Received UDP {len(data)} bytes from {ip}:{port} -> {data!r}")
    try:
        time.sleep(.5)
        udp_sock.sendto(UDP_REPLY_MSG, (ip, port))
        print(f"[>] Sent UDP reply to {ip}:{port}")
        return ip, True
    except Exception as e:
        print(f"[!] Failed to send UDP reply to {ip}:{port}: {e}")
    return None, False


def send_servo_pos_packet(ip, msg):
    try:
        with socket.create_connection((ip, CONTROL_PORT), timeout=5) as s:
            s.sendall(msg)
            s.settimeout(.1) # increase this number if the packet is getting cut short
            s.recv(4096)
    except socket.timeout:
        pass
    except Exception as e:
        print(f"[!] TCP connect/send to {ip}:{CONTROL_PORT} failed: {e}")


if __name__ == "__main__":
    # Create UDP socket to receive broadcasts
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # allow reuse
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # allow receiving broadcast packets
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # bind to all interfaces on DISCOVERY_PORT
        udp_sock.bind(("", DISCOVERY_PORT))
    except PermissionError:
        print(f"[!] PermissionError: change the port number so it is >1024 and <65536.")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to create/bind UDP socket: {e}")
        sys.exit(1)

    has_connected = False
    esp_ip = None
    while not has_connected:
        try:
            # Blocking receive. buffer size 4096 is arbitrary and should be enough for small payloads.
            print("beginning listening")
            data, addr = udp_sock.recvfrom(4096)
            print("done listening")
            esp_ip, has_connected = handle_incoming_udp(data, addr)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            # Keep running on transient errors
            print(f"[!] Error while receiving/handling packet: {e}")
            time.sleep(0.5)

    print(esp_ip)

    time.sleep(.2)

    try:
        while True:
           # do some calculations, then edit these values to be the "correct" angles (in reality there will be 12 not 8 numbers, as there are 12 servos.
           # however, for now just get it to work on one leg (first three numbers) and when we buy the other servos we can expand the array to length 12
            packet_to_send = [0,0,0,0,0,0,0,0]
            packet_to_send[0] = int(input())
            packet_to_send[1] = int(input())
            packet_to_send[2] = int(input())
            if packet_to_send is not None:
                print(packet_to_send)
                send_servo_pos_packet(esp_ip, bytes(packet_to_send))
            time.sleep(0.01)
    except Exception as error:
        print(error)
        pass
