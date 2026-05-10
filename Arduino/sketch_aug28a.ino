#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h> 
#include <LiquidCrystal_I2C.h>

// --- CONFIGURATION ---
#define SS_PIN    10 // RFID SS Pin
#define RST_PIN   9  // RFID RST Pin
#define LCD_ADDRESS 0x27 
#define LCD_COLS 16
#define LCD_ROWS 2
// --- END CONFIGURATION ---

MFRC522 mfrc522(SS_PIN, RST_PIN);
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

String incomingMessage = ""; // for storing incoming serial data

// **1. NEW: Define the custom smiley character**
// (8 rows of 5 pixels)
byte smiley[8] = {
  B00000,
  B01010,
  B01010,
  B00000,
  B10001,
  B01110,
  B00000,
  B00000
};

void setup() {
  Serial.begin(9600); 
  while (!Serial);
  SPI.begin();
  mfrc522.PCD_Init();
  
  lcd.init();
  lcd.backlight();
  
  // **2. NEW: Create the custom smiley and store it in LCD memory slot 0**
  lcd.createChar(0, smiley); 
  
  displayMessage("Library Kiosk", "Scan Card...");
}

void loop() {
  // 1. Check for incoming response from Python first
  if (Serial.available() > 0) {
    incomingMessage = Serial.readStringUntil('\n');
    processMessage(incomingMessage);
  }

  // 2. Look for new RFID cards
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // 3. A card has been detected, get its UID
  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidString += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uidString += String(mfrc522.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();

  // 4. Print the UID to the serial port for Python to read
  Serial.println(uidString);
  
  // 5. Show a "Verifying" message on the LCD
  displayMessage("Verifying...", uidString);
}

// Handles the response from the Python script
void processMessage(String message) {
  message.trim(); // Remove any whitespace

  if (message.startsWith("SUCCESS:")) {
    // Message is "SUCCESS:Munish Kumar"
    String name = message.substring(8); // Get the name part
    
    // **3. MODIFIED: Print the welcome message with the custom smiley**
    lcd.clear();
    lcd.setCursor(0, 0); // Go to first line
    lcd.print("Welcome, ");
    lcd.write(byte(0)); // Print custom char 0 (the smiley)
    
    lcd.setCursor(0, 1); // Go to second line
    lcd.print(name);
  } 
  else if (message.startsWith("ERROR:")) {
    // Message is "ERROR:RFID Not Found"
    String errorMsg = message.substring(6); // Get the error part
    displayMessage("Access Denied", errorMsg);
  }

  // After 3 seconds, go back to the default screen
  delay(3000);
  displayMessage("Library Kiosk", "Scan Card...");
}

// Helper function to print to the LCD
void displayMessage(String line1, String line2) {
  lcd.clear();
  
  lcd.setCursor(0, 0);
  lcd.print(line1);
  
  lcd.setCursor(0, 1);
  lcd.print(line2);
}