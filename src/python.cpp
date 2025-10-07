#include <Arduino.h>
#include <Servo.h>
// put function declarations here:
Servo hipServo1, kneeServo1; // For a knee joint
Servo hipServo2, kneeServo2;
Servo hipServo3, kneeServo3;
Servo hipServo4, kneeServo4;
// Add more for other joints as needed


void forward();

void setup() {
void liftLeg(Servo& hipServo, Servo& kneeServo,
             Servo& hipServoAlt, Servo& kneeServoAlt,
             int delaySpeed, int angle);  

  hipServo1.attach(9); 
  kneeServo1.attach(10); 
  hipServo2.attach(11); 
  kneeServo2.attach(12); 
  hipServo3.attach(13); 
  kneeServo3.attach(14); 
  hipServo4.attach(15); 
  kneeServo4.attach(16); 


}

void loop() {
  // put your main code here, to run repeatedly:
}

void forward() {
  liftLeg(hipServo1, kneeServo1, hipServo4, kneeServo4, 10, 45, 45);
  delay(25);
  liftLeg(hipServo2, kneeServo2, hipServo3, kneeServo3, 10, 45, 45);
}


void liftLeg(Servo& hipServo, Servo& kneeServo, Servo& hipServoalt, Servo& kneeServoAlt, int delaySpeed, int hipAngle, int kneeAngle) {
  double hipKneeAngleRatio = (double) hipAngle / (double) kneeAngle;

  for (int i = 0; i < hipAngle; i++) {
    hipServo.write(i);
    kneeServo.write(i * hipKneeAngleRatio);
    hipServoAlt.write(i);
    kneeServoAlt.write(i * hipKneeAngleRatio);
    delay(delaySpeed);
  }
}


