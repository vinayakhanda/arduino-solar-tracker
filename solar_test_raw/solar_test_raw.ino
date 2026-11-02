const int analogPin = A5;
const float V_REF = 5.0; // Change to 3.3 if using a 3.3V board (e.g. ESP32, 3.3V Pro Mini)

void setup() {
  Serial.begin(9600);
}

void loop() {
  int rawADC = analogRead(analogPin);
  
  // Calculate voltage present at pin A7
  float vPin = (rawADC * V_REF) / 1023.0; 
  
  // Multiply by 2 to reconstruct the original input voltage
  float vIn = vPin * 2.0; 

  Serial.print("Pin A7 Voltage: ");
  Serial.print(vPin);
  Serial.print(" V | Original Input: ");
  Serial.print(vIn);
  Serial.println(" V");

  delay(500);
}