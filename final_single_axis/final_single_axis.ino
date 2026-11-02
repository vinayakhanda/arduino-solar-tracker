
#include <Servo.h>

// ================================
// PIN DEFINITIONS
// ================================

const int ldrLeftPin = A0;
const int ldrRightPin = A1;
const int servoPin = 10;

// ================================
// SERVO CONFIGURATION
// ================================

Servo trackerServo;

int servoPosition = 90;  // Starting position

const int minLimit = 10;
const int maxLimit = 170;

// ================================
// TRACKING CONFIGURATION
// ================================

const int tolerance = 20;
const int delayTime = 100;

// ================================
// SETUP
// ================================

void setup() {

  Serial.begin(9600);

  trackerServo.attach(servoPin);

  // Move servo to starting position
  trackerServo.write(servoPosition);

  delay(500);

  Serial.println("==============================");
  Serial.println("     SOLAR TRACKER STARTED");
  Serial.println("==============================");

  Serial.print("Initial Servo Position: ");
  Serial.println(servoPosition);
}

// ================================
// MAIN LOOP
// ================================

void loop() {

  // Read LDR sensor values
  int ldrLeft = analogRead(ldrLeftPin);
  int ldrRight = analogRead(ldrRightPin);

  // Calculate difference
  int difference = abs(ldrLeft - ldrRight);

  // Default tracking state
  const char* state = "STABLE";

  // Check whether adjustment is needed
  if (difference > tolerance) {

    // More light on the left
    if (ldrLeft > ldrRight) {

      if (servoPosition > minLimit) {

        servoPosition--;
        state = "MOVING LEFT";

      } else {

        state = "MIN LIMIT REACHED";

      }
    }

    // More light on the right
    else if (ldrRight > ldrLeft) {

      if (servoPosition < maxLimit) {

        servoPosition++;
        state = "MOVING RIGHT";

      } else {

        state = "MAX LIMIT REACHED";

      }
    }

    // Update servo position
    trackerServo.write(servoPosition);
  }

  // ================================
  // SERIAL MONITOR OUTPUT
  // ================================

  Serial.print("L: ");
  Serial.print(ldrLeft);

  Serial.print(" | R: ");
  Serial.print(ldrRight);

  Serial.print(" | Diff: ");
  Serial.print(difference);

  Serial.print(" | Pos: ");
  Serial.print(servoPosition);

  Serial.print(" | State: ");
  Serial.println(state);

  // Small delay between readings
  delay(delayTime);
}
