#include <Servo.h>

Servo rotateServo;
Servo tiltServo;

// LDR connections
const int ldrLeft = A0;
const int ldrRight = A1;

// Servo signal pins
const int rotatePin = 10;
const int tiltPin = 9;

// Centre position
const int centerAngle = 90;

// Current servo angles
int rotateAngle = centerAngle;
int tiltAngle = centerAngle;

// Servo limits
const int minAngle = 0;
const int maxAngle = 180;

// Tracking settings
const int tolerance = 5;
const int stepSize = 1;
const int minLight = 80;
const int samples = 10;

// Read average LDR value
int readLDR(int pin) {
  long total = 0;

  for (int i = 0; i < samples; i++) {
    total += analogRead(pin);
    delay(3);
  }

  return total / samples;
}

// Send angles to both servos
void moveServos() {
  rotateServo.write(rotateAngle);
  tiltServo.write(tiltAngle);
}

void setup() {
  Serial.begin(9600);

  rotateServo.attach(rotatePin);
  tiltServo.attach(tiltPin);

  rotateAngle = centerAngle;
  tiltAngle = centerAngle;

  moveServos();

  delay(500);

  Serial.println("SOLAR TRACKER STARTED");
  Serial.println("Night/equal-light position: 90 degrees");
  Serial.println("----------------------------------------");
}

void loop() {
  int leftValue = readLDR(ldrLeft);
  int rightValue = readLDR(ldrRight);

  int difference = leftValue - rightValue;
  int averageLight = (leftValue + rightValue) / 2;

  Serial.print("Left LDR: ");
  Serial.print(leftValue);

  Serial.print(" | Right LDR: ");
  Serial.print(rightValue);

  Serial.print(" | Difference: ");
  Serial.print(difference);

  // NIGHT: return both servos to centre
  if (averageLight < minLight) {
    rotateAngle = centerAngle;
    tiltAngle = centerAngle;

    moveServos();

    Serial.print(" | NIGHT - CENTRED");
  }

  // EQUAL LIGHT: return both servos to centre
  else if (abs(difference) <= tolerance) {
    rotateAngle = centerAngle;
    tiltAngle = centerAngle;

    moveServos();

    Serial.print(" | EQUAL LIGHT - CENTRED");
  }

  // LEFT LDR receives more light
  else if (difference > tolerance) {
    rotateAngle = constrain(
      rotateAngle + stepSize, minAngle, maxAngle
    );

    tiltAngle = constrain(
      tiltAngle + stepSize, minAngle, maxAngle
    );

    moveServos();

    Serial.print(" | TRACKING LEFT");
  }

  // RIGHT LDR receives more light
  else {
    rotateAngle = constrain(
      rotateAngle - stepSize, minAngle, maxAngle
    );

    tiltAngle = constrain(
      tiltAngle - stepSize, minAngle, maxAngle
    );

    moveServos();

    Serial.print(" | TRACKING RIGHT");
  }

  Serial.print(" | Rotation angle: ");
  Serial.print(rotateAngle);

  Serial.print(" | Tilt angle: ");
  Serial.println(tiltAngle);

  delay(100);
}