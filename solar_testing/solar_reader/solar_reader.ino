const int solarPin = A7; 

// Safer resistor combination values
const float R1 = 22000.0; // Your 22k/23k resistor
const float R2 = 22000.0;  // Your 4.7k resistor

void setup() {
  Serial.begin(9600); 
  Serial.println("--- Upgraded Safe Solar Monitor ---");
}

void loop() {
  int rawADC = analogRead(solarPin); 
  
  float pinVoltage = rawADC * (5.0 / 1023.0); 
  
  // New math for the unequal resistor divider
  float solarPanelVoltage = pinVoltage * ((R1 + R2) / R2); 
  
  Serial.print("Pin A0 Voltage: ");
  Serial.print(pinVoltage, 2);
  Serial.print("V (Now safely below 5V) | Solar Panel Total: ");
  Serial.print(solarPanelVoltage, 2);
  Serial.println(" V");
  
  delay(1000); 
}
