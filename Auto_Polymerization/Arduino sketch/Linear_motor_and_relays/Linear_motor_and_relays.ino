#include <Servo.h>

Servo actuator;
int actuatorPin = 10;
int precip_relayPin = 9;
int gas_relayPin = 6;

// Track the current state of each relay
bool precipRelayState = false;
bool gasRelayState = false;

void setup() {
  actuator.attach(actuatorPin);
  pinMode(precip_relayPin, OUTPUT);
  pinMode(gas_relayPin, OUTPUT);

  // Optional: start in a known safe state
  //digitalWrite(precip_relayPin, LOW);
  //digitalWrite(gas_relayPin, LOW);
  //actuator.writeMicroseconds(1000);

  Serial.begin(9600);
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();  // Make commands case-insensitive

    int val = input.toInt();
    if (val >= 1000 && val <= 2000) {
      actuator.writeMicroseconds(val);
      Serial.println("Actuator set to: " + String(val));
    } 
    else if (input == "PRECIP_ON") {
      precipRelayState = true;
      digitalWrite(precip_relayPin, HIGH);
      Serial.println("Precipitation Relay ON");
    } 
    else if (input == "PRECIP_OFF") {
      precipRelayState = false;
      digitalWrite(precip_relayPin, LOW);
      Serial.println("Precipitation Relay OFF");
    } 
    else if (input == "GAS_ON") {
      gasRelayState = true;
      digitalWrite(gas_relayPin, HIGH);
      Serial.println("Gas Relay ON");
    } 
    else if (input == "GAS_OFF") {
      gasRelayState = false;
      digitalWrite(gas_relayPin, LOW);
      Serial.println("Gas Relay OFF");
    } 
    else if (input == "ALL_ON") {
      precipRelayState = true;
      gasRelayState = true;
      digitalWrite(precip_relayPin, HIGH);
      digitalWrite(gas_relayPin, HIGH);
      Serial.println("Both relays ON");
    } 
    else if (input == "ALL_OFF") {
      precipRelayState = false;
      gasRelayState = false;
      digitalWrite(precip_relayPin, LOW);
      digitalWrite(gas_relayPin, LOW);
      Serial.println("Both relays OFF");
    } 
    else if (input == "STATUS") {
      Serial.print("Precipitation Relay: ");
      Serial.println(precipRelayState ? "ON" : "OFF");
      Serial.print("Gas Relay: ");
      Serial.println(gasRelayState ? "ON" : "OFF");
    } 
    else {
      Serial.println("Invalid command: " + input);
    }
  }
}