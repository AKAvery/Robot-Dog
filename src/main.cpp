#include <Arduino.h>
#include <Servo.h>


// put function declarations here:
Servo hipServo2, kneeServo2;
Servo hipServo3, kneeServo3;
Servo hipServo4, kneeServo4;
// Add more for other joints as needed

void runServo();

void setup() {
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


void runServo(Servo& servo, int angle) {
    servo.write(angle);
}
 
