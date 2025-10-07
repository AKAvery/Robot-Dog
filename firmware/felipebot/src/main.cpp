#include <Arduino.h>
#include <Servo.h>
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
void moveServo(int pin, int angle)
{
    servos[pin].write(angle);
}

void handleServoControl()
{
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    if (webServer.hasArg("pin") && webServer.hasArg("angle"))
    {
        int pin = webServer.arg("pin").toInt();
        int angle = webServer.arg("angle").toInt();
        moveServo(pin, angle); // Actually move the servo
        String reply = "Moved servo on pin " + String(pin) + " to angle " + String(angle);
        webServer.send(200, "text/plain", reply);
    }
    else
    {
        webServer.send(400, "text/plain", "Missing pin or angle parameter");
    }
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