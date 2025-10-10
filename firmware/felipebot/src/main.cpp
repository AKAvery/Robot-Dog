#include <Arduino.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <WebServer.h>


// constants
const char *ssid = "robotdog-ap";
const char *password = "felipedog";

WebServer webServer(80);
// array of 8 servos connected to digital pins 12-19
Servo servos[8];
int servoPins[8] = {12, 13, 14, 15, 16, 17, 18, 19};

// forward declaration of functions
void handleServoControl();
void moveServo(int pin, int angle);
void startAccessPoint();
void startWebServer();
void initializeServos();

void setup() // RUNS ONCE
{
    Serial.begin(115200);
    startAccessPoint();
    startWebServer();
    initializeServos();
}

void loop() // RUNS REPEATEDLY
{
    webServer.handleClient();
}

// put function definitions here:
void handleOptions() {
  webServer.sendHeader("Access-Control-Allow-Origin",  "*");
  webServer.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  webServer.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  webServer.sendHeader("Access-Control-Max-Age", "600"); // cache preflight 10 min
  webServer.send(204);
}

static inline bool validIndex(int idx) { return idx >= 0 && idx < 8; }

void moveServo(int pin, int angle)
{
    if (validIndex(pin)) {
        servos[pin].write(constrain(angle, 0, 180));
    }
}

void handleServoControl()
{
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    if (webServer.hasArg("pin") && webServer.hasArg("angle"))
    {
        int pin = webServer.arg("pin").toInt();
        int angle = webServer.arg("angle").toInt();
        if (!validIndex(pin)) { webServer.send(400, "text/plain", "Bad index (0..7)"); return; }
        moveServo(pin, angle); // Actually move the servo
        String reply = "Moved servo on pin " + String(pin) + " to angle " + String(angle);
        webServer.send(200, "text/plain", reply);
    }
    else
    {
        webServer.send(400, "text/plain", "Missing pin or angle parameter");
    }
}

void handleMovePair() {
  webServer.sendHeader("Access-Control-Allow-Origin", "*");

  if (!webServer.hasArg("i1") || !webServer.hasArg("a1") ||
      !webServer.hasArg("i2") || !webServer.hasArg("a2")) {
    webServer.send(400, "text/plain", "Missing i1,a1,i2,a2");
    return;
  }

  int i1 = webServer.arg("i1").toInt();
  int a1 = webServer.arg("a1").toInt();
  int i2 = webServer.arg("i2").toInt();
  int a2 = webServer.arg("a2").toInt();

if (!validIndex(i1) || !validIndex(i2)) { webServer.send(400, "text/plain", "Bad index (0..7)"); return; }


  servos[i1].write(constrain(a1, 0, 180));
  servos[i2].write(constrain(a2, 0, 180));

  webServer.send(200, "text/plain", "OK");
}

void startAccessPoint()
{
    // Connect to Wi-Fi network with SSID and password
    Serial.print("Setting AP (Access Point)…");
    // Remove the password parameter, if you want the AP (Access Point) to be open
    WiFi.softAP(ssid, password);

    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP IP address: ");
    Serial.println(IP);
}

void startWebServer()
{
    webServer.on("/moveServo", handleServoControl);
    webServer.on("/movePair", handleMovePair);
    webServer.on("/moveServo", HTTP_OPTIONS, handleOptions);
    webServer.on("/movePair", HTTP_OPTIONS, handleOptions);
    webServer.begin();
    Serial.println("HTTP server started");
}

void initializeServos()
{
    for (int i = 0; i < 8; i++)
    {
        servos[i].attach(servoPins[i]);
    }
}

