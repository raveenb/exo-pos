/*
 * Buzzer Test - Minimal sketch to diagnose hardware issue
 *
 * This sketch does NOTHING except:
 * 1. Set buzzer pin to OUTPUT
 * 2. Force it LOW (off)
 * 3. Print status every second
 *
 * If buzzer still beeps with this code, it's a hardware problem.
 */

#define BUZZER_PIN 3

void setup() {
  Serial.begin(115200);

  // Configure buzzer pin
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Force OFF

  Serial.println("Buzzer Test Started");
  Serial.println("Buzzer pin set to OUTPUT and LOW");
  Serial.println("If you hear beeping, it's a hardware issue!");
  Serial.println("");
}

void loop() {
  // Explicitly force buzzer OFF every loop
  digitalWrite(BUZZER_PIN, LOW);

  // Print status
  Serial.print("Loop ");
  Serial.print(millis() / 1000);
  Serial.println("s - Buzzer forced LOW");

  delay(1000);
}
