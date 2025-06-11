# linear_actuator_control

A simple Python package for controlling an Actuonix linear actuator via an Arduino board using a serial connection.


## Installation
pip install linear_actuator_control

Or, to install from source:

pip install .


## Requirements

- Python 3.7 or higher
- Arduino with firmware that receives PWM values via serial
- Dependency: `pyserial`


## Arduino Example Code
The Arduino has to be connected to an at least 6 V power supply to drive the actuator.
Upload the following code to your Arduino. It receives PWM values via serial and controls the actuator accordingly.


#include <Servo.h>

Servo actuator;
int position;

void setup() {
  actuator.attach(8); // Connect actuator signal wire to GPIO8
  Serial.begin(9600); // Start serial communication
}

void loop() {
  if (Serial.available()) {
    int input = Serial.parseInt(); // Read an integer from Serial

    if (input >= 1000 && input <= 2000) {
      actuator.writeMicroseconds(input);
      Serial.print("Moved to: ");
      Serial.println(input);
    }
  }
}


## Usage
from linear_actuator_control.Linear_actuator_control import move_actuator

- The package automatically searches for a connected Arduino (the port description must contain "Arduino").
- The function `move_actuator(pwm_value)` sends a PWM value (1000–2000) to the Arduino to control the actuator.
    - 1000 = fully retracted
    - 2000 = fully extended (10 cm)


## Notes

- Ensure the Arduino is connected and running the appropriate firmware.
- The serial connection can be closed with `arduino.close()` if needed (optional).


## License

MIT
