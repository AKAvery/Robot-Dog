#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>

const char* WIFI_SSID = "robot-dog";
const char* WIFI_PASS = "some wifi password";

// Ports and secret, make the ports unique and 1024 < (DISCOVERY_PORT != CONTROL_PORT) < 65536
const uint16_t DISCOVERY_PORT = -1;   // UDP discovery
const uint16_t CONTROL_PORT   = -2;   // TCP control 
const char* SECRET_KEY = "some secret key"; //make sure this matches the secret key in the python side

const uint8_t num_servos = 8; //ill change to 12 later
const uint8_t servo_pins[] = {13, 12, 14, 27, 26, 25, 33, 32};
Servo servos[num_servos];

// Discovery timing
const unsigned long BROADCAST_INTERVAL_MS = 1500; // send a broadcast every 1.5s until paired
const unsigned long DISCOVERY_CHECK_MS = 100; // how often we check for incoming replies
const uint TCP_READ_TIMEOUT_MS = 3000;


WiFiUDP udp;
WiFiServer controlServer(CONTROL_PORT);
const int LEN_RCV_ARR = 8; //change this according to the length of the array you send on the python side

// pairing state
bool paired = false;
IPAddress pairedIP;
unsigned long lastBroadcastMillis = 0;

void useReceivedData(uint8_t arr[]) {
  servos[0].write(arr[0]);
  servos[1].write(arr[1]);
  servos[2].write(arr[2]);
}

void setupWiFi() {
  Serial.printf("Connecting to WiFi '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print('.');
    if (millis() - start > 30000) {
      Serial.println("\nWiFi connect failed - restarting...");
      ESP.restart();
    }
  }
  Serial.println();
  Serial.print("WiFi connected. IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Subnet mask: ");
  Serial.println(WiFi.subnetMask());
}

void sendDiscoveryBroadcast() {
  IPAddress bcast = IPAddress(255, 255, 255, 255);
  const char* msg = SECRET_KEY;
  udp.beginPacket(bcast, DISCOVERY_PORT);
  udp.write((const uint8_t*) msg, strlen(msg));
  udp.endPacket();
  Serial.printf("Broadcasted discovery to %s:%u\n", bcast.toString().c_str(), DISCOVERY_PORT);
}

bool checkDiscoveryReplies() {
  int packetSize = udp.parsePacket();
  if (packetSize <= 0) return false;
  // read packet
  char buf[512];
  int len = udp.read(buf, sizeof(buf)-1);
  if (len <= 0) return false;
  buf[len] = '\0';
  IPAddress remote = udp.remoteIP();
  uint16_t remotePort = udp.remotePort();
  Serial.printf("UDP packet from %s:%u -> %s\n", remote.toString().c_str(), remotePort, buf);

  // If the payload contains SECRET_KEY anywhere, accept
  if (strstr(buf, SECRET_KEY) != nullptr) {
    pairedIP = remote;
    paired = true;
    Serial.printf("Paired with %s (secret found in UDP reply)\n", pairedIP.toString().c_str());
    return true;
  }
  return false;
}

void handleControlClient(WiFiClient &client) {
  // Only accept commands from pairedIP
  IPAddress remote = client.remoteIP();
  if (remote != pairedIP) {
    Serial.printf("Rejected TCP connection from unauthorized IP %s\n", remote.toString().c_str());
    client.stop();
    return;
  }
  // Serial.printf("inc %s : ", remote.toString().c_str());
  client.setTimeout(TCP_READ_TIMEOUT_MS); // 3s timeout for reading commands
  uint8_t rcv_arr[LEN_RCV_ARR];
  unsigned long start = millis();
  uint servo_index = 0;
  while (millis() - start < TCP_READ_TIMEOUT_MS && client.connected()) {
    if (client.available()) {
      uint8_t c = client.read();
      rcv_arr[servo_index++] = c;
      if (servo_index > LEN_RCV_ARR) break;
    } else {
      delay(2);
    }
  }
  Serial.print("rcv arr: ");
  for (int iter = 0; iter < LEN_RCV_ARR; iter++) {
    Serial.print(rcv_arr[iter]);
    Serial.print(" ");
  }

  useReceivedData(rcv_arr);

  client.stop();
  Serial.println("end");
}

void setup() {
  Serial.begin(115200);
  delay(200);

  for (uint8_t iter = 0; iter < num_servos; iter++) {
    // servos[iter].setPeriodHertz(50);
    servos[iter].attach(servo_pins[iter], 500, 1833);
    servos[iter].write(96);
  }

  // flw.setPeriodHertz(50);
  // flw.attach(servo_pins[0], 500, 1833); // 2500 would be 270 degrees
  // flw.write(90);


  setupWiFi();
  // start UDP for discovery
  if (udp.begin(DISCOVERY_PORT) == 1) {
    Serial.printf("UDP discovery listening on port %u\n", DISCOVERY_PORT);
  } else {
    Serial.printf("Failed to begin UDP on port %u (but continuing)\n", DISCOVERY_PORT);
  }
  while (!paired) {
    Serial.print("*");
    unsigned long now = millis();
    if (now - lastBroadcastMillis >= BROADCAST_INTERVAL_MS) {
      sendDiscoveryBroadcast();
      lastBroadcastMillis = now;
    }
    delay(DISCOVERY_CHECK_MS);
    // check UDP replies repeatedly
    if (checkDiscoveryReplies()) {
      // paired becomes true inside checkDiscoveryReplies()
      // stop UDP discovery (we can keep the UDP object but stop reading)
      udp.stop();
      Serial.println("Stopped UDP discovery.");
      // start the TCP control server
      controlServer.begin();
      Serial.printf("TCP control server started on port %u. Waiting for connections from %s\n", CONTROL_PORT, pairedIP.toString().c_str());
    }
  }

}

void loop() {
  WiFiClient client = controlServer.available();
  if (client) {
    handleControlClient(client);
  }
  // small sleep to yield
  delay(5);
}
