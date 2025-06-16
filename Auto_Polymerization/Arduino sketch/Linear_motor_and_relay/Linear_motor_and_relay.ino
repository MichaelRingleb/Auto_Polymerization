#include <Servo.h>

Servo actuator;
int actuatorPin = 8;      //  Actuator controlled by signal on pin 8
int relayPin = 9;         //  Relay for solenoid valve on pin 9

void setup() {
  actuator.attach(actuatorPin);         // Servo/Actuator signal
  pinMode(relayPin, OUTPUT);            // Relay control provided by setting the pin as an output pin
  //digitalWrite(relayPin, LOW);        // Start with relay OFF

  Serial.begin(9600);
  //actuator.writeMicroseconds(1000);     // Initial actuator position
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');              // Reads until Line-end

    input.trim();                                             // trims whitespaces and linebreaks

    if (input.toInt() >= 1000 && input.toInt() <= 2000) {     // if serial input string is between "1000" and "2000"
      actuator.writeMicroseconds(input.toInt());              //  send value to actuator which will then move to the required position (1000 = 0 cm, 2000 = 10 cm)
    } else if (input == "ON") {                               // if input == ON
      digitalWrite(relayPin, HIGH);                           // set PinMode which will trigger the relay and hence, the solenoid valve
    } else if (input == "OFF") {                              // if input == OFF
      digitalWrite(relayPin, LOW);                            // set PinMode which will trigger the relay and hence, the solenoid valve
    }
  }
}