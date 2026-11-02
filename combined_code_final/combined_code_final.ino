#include <Servo.h>

// ================================
// PIN DEFINITIONS
// ================================
const int ldrLeftPin = A0;      // Left LDR sensor pin
const int ldrRightPin = A1;     // Right LDR sensor pin
const int voltagePin = A5;      // Voltage sensor analog pin
const int servoPin = 10;        // Servo signal pin

// ================================
// SERVO CONFIGURATION
// ================================
Servo trackerServo;
int servoPosition = 90;         // Starting position
const int minLimit = 10;        // Minimum servo angle
const int maxLimit = 170;       // Maximum servo angle

// ================================
// TRACKING & VOLTAGE CONFIGURATION
// ================================
const int tolerance = 10;       // Light difference threshold
const float V_REF = 5.0;        // Reference voltage (5.0V for UNO/Nano)

// Non-blocking timer intervals
const unsigned long trackerInterval = 100; // Tracking update every 100 ms
const unsigned long voltageInterval = 500; // Voltage update every 500 ms

unsigned long lastTrackerTime = 0;
unsigned long lastVoltageTime = 0;

// Global voltage variables for telemetry transmission
float currentVPin = 0.0;
float currentVIn = 0.0;

void setup() {
  Serial.begin(9600);
  trackerServo.attach(servoPin);
  trackerServo.write(servoPosition);
  delay(500);

  Serial.println("SYSTEM:INITIALIZED");
}

void loop() {
  unsigned long currentMillis = millis();

  // 1. VOLTAGE MONITORING TASK (Every 500 ms)
  if (currentMillis - lastVoltageTime >= voltageInterval) {
    lastVoltageTime = currentMillis;

    int rawADC = analogRead(voltagePin);
    currentVPin = (rawADC * V_REF) / 1023.0;
    currentVIn = currentVPin * 2.0; // Divider factor (x2)
  }

  // 2. SOLAR TRACKING & SERIAL TELEMETRY (Every 100 ms)
  if (currentMillis - lastTrackerTime >= trackerInterval) {
    lastTrackerTime = currentMillis;

    int ldrLeft = analogRead(ldrLeftPin);
    int ldrRight = analogRead(ldrRightPin);
    int difference = abs(ldrLeft - ldrRight);
    const char* state = "STABLE";

    if (difference > tolerance) {
      if (ldrLeft > ldrRight) {
        if (servoPosition > minLimit) {
          servoPosition--;
          state = "MOVING LEFT";
        } else {
          state = "MIN LIMIT";
        }
      } else if (ldrRight > ldrLeft) {
        if (servoPosition < maxLimit) {
          servoPosition++;
          state = "MOVING RIGHT";
        } else {
          state = "MAX LIMIT";
        }
      }
      trackerServo.write(servoPosition);
    }

    // Key-value output formatted for Python parser
    Serial.print("LDR_L:");
    Serial.print(ldrLeft);
    Serial.print(",LDR_R:");
    Serial.print(ldrRight);
    Serial.print(",DIFF:");
    Serial.print(difference);
    Serial.print(",POS:");
    Serial.print(servoPosition);
    Serial.print(",STATE:");
    Serial.print(state);
    Serial.print(",VPIN:");
    Serial.print(currentVPin, 2);
    Serial.print(",VIN:");
    Serial.println(currentVIn, 2);
  }
}