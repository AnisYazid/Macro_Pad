#include <EEPROM.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HID-Project.h>


const uint8_t SWITCH_PINS[] = {6, 16, 7, 10, 8, 5, 14, 15, 9};
const uint8_t KEY_COUNT = sizeof(SWITCH_PINS) / sizeof(SWITCH_PINS[0]);
#define ENC_S1 A2
#define ENC_S2 A1
#define ENC_KEY A0
#define OLED_WIDTH 128
#define OLED_HEIGHT 32
#define OLED_ADDRESS 0x3C

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
String keyCombos[KEY_COUNT] = {};
bool wasPressed[KEY_COUNT] = {false, false, false, false, false, false, false, false, false};
String serialLine;
const char *const ENCODER_EVENTS[] = {"CW", "CCW", "DOUBLE_PRESS"};
const uint8_t ENCODER_EVENT_COUNT = 3;
const uint8_t EEPROM_ENCODER_SIZE = 18;
String encoderActions[ENCODER_EVENT_COUNT] = {};
uint8_t encoderSensitivity = 3;
uint8_t encoderState;
int8_t encoderAccumulator = 0;
bool encoderButtonWasDown = false;
uint8_t encoderClickCount = 0;
unsigned long encoderButtonAt = 0;
unsigned long encoderLastClickAt = 0;
String profileName = "Default";

const int EEPROM_KEY_SIZE = 97;
const int EEPROM_KEY_BASE = 0;
const int EEPROM_ENCODER_BASE = EEPROM_KEY_BASE + KEY_COUNT * EEPROM_KEY_SIZE;
const int EEPROM_PROFILE_BASE = EEPROM_ENCODER_BASE + ENCODER_EVENT_COUNT * EEPROM_ENCODER_SIZE;

int encoderEventIndex(const String &event) {
  for (uint8_t i = 0; i < ENCODER_EVENT_COUNT; i++) {
    if (event == ENCODER_EVENTS[i]) return i;
  }
  return -1;
}

uint8_t encoderActionRepeats() {
  return 2 + ((uint16_t)encoderSensitivity * 38 + 5) / 10;
}

void loadFixedString(int address, uint8_t capacity, String &target) {
  char saved[25];
  uint8_t length = EEPROM.read(address);
  if (length >= capacity) {
    target = "";
    return;
  }
  for (uint8_t i = 0; i < length; i++) saved[i] = EEPROM.read(address + 1 + i);
  saved[length] = '\0';
  target = String(saved);
}

void saveFixedString(int address, uint8_t capacity, const String &value) {
  String clipped = value.substring(0, capacity - 1);
  EEPROM.update(address, clipped.length());
  for (uint8_t i = 0; i < clipped.length(); i++) EEPROM.update(address + 1 + i, clipped.charAt(i));
  EEPROM.update(address + 1 + clipped.length(), '\0');
}

void showOLED(const String &line1, const String &line2 = "") {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("NISSOU MACROPAD");
  display.drawLine(0, 10, OLED_WIDTH - 1, 10, SSD1306_WHITE);
  display.setCursor(0, 14);
  display.println(line1.substring(0, 21));
  display.setCursor(0, 24);
  display.println(line2.substring(0, 21));
  display.display();
}

void showAction(const String &action) {
  String status = "S" + String(encoderSensitivity) + " | " +
                  (action.length() ? action : "Ready");
  showOLED(profileName, status);
}

void emitEncoderEvent(const String &event) {
  Serial.println("EVENT," + event);
}

void loadSavedKeys() {
  for (uint8_t i = 0; i < KEY_COUNT; i++) {
    int address = EEPROM_KEY_BASE + i * EEPROM_KEY_SIZE;
    uint8_t length = EEPROM.read(address);
    if (length >= EEPROM_KEY_SIZE) {
      keyCombos[i] = "";
      continue;
    }
    char saved[EEPROM_KEY_SIZE];
    for (uint8_t j = 0; j < length; j++) {
      saved[j] = EEPROM.read(address + 1 + j);
    }
    saved[length] = '\0';
    keyCombos[i] = String(saved);
  }
  for (uint8_t i = 0; i < ENCODER_EVENT_COUNT; i++) {
    loadFixedString(EEPROM_ENCODER_BASE + i * EEPROM_ENCODER_SIZE,
                    EEPROM_ENCODER_SIZE, encoderActions[i]);
  }
  loadFixedString(EEPROM_PROFILE_BASE, EEPROM_ENCODER_SIZE, profileName);
  encoderSensitivity = EEPROM.read(EEPROM_PROFILE_BASE + EEPROM_ENCODER_SIZE);
  if (encoderSensitivity < 1 || encoderSensitivity > 40) encoderSensitivity = 3;
}

void saveKeys() {
  for (uint8_t i = 0; i < KEY_COUNT; i++) {
    int address = EEPROM_KEY_BASE + i * EEPROM_KEY_SIZE;
    String value = keyCombos[i];
    if (value.length() >= EEPROM_KEY_SIZE) {
      value = value.substring(0, EEPROM_KEY_SIZE - 1);
    }
    uint8_t length = value.length();
    EEPROM.update(address, length);
    for (uint8_t j = 0; j < length; j++) {
      EEPROM.update(address + 1 + j, value.charAt(j));
    }
    EEPROM.update(address + 1 + length, '\0');
  }
  for (uint8_t i = 0; i < ENCODER_EVENT_COUNT; i++) {
    saveFixedString(EEPROM_ENCODER_BASE + i * EEPROM_ENCODER_SIZE,
                    EEPROM_ENCODER_SIZE, encoderActions[i]);
  }
  saveFixedString(EEPROM_PROFILE_BASE, EEPROM_ENCODER_SIZE, profileName);
  EEPROM.update(EEPROM_PROFILE_BASE + EEPROM_ENCODER_SIZE, encoderSensitivity);
}

void setup() {
  for (uint8_t i = 0; i < KEY_COUNT; i++) {
    pinMode(SWITCH_PINS[i], INPUT_PULLUP);
  }
  pinMode(ENC_S1, INPUT_PULLUP);
  pinMode(ENC_S2, INPUT_PULLUP);
  pinMode(ENC_KEY, INPUT_PULLUP);
  encoderState = (digitalRead(ENC_S1) << 1) | digitalRead(ENC_S2);

  Serial.begin(115200);
  Keyboard.begin();
  Consumer.begin();
  Mouse.begin();
  serialLine.reserve(96);
  loadSavedKeys();
  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  showOLED(profileName, "S" + String(encoderSensitivity) + " | Ready");
}

void loop() {
  readSerialCommands();
  readKeys();
  readEncoder();
}

void readKeys() {
  for (uint8_t i = 0; i < KEY_COUNT; i++) {
    bool pressed = digitalRead(SWITCH_PINS[i]) == LOW;
    if (pressed && !wasPressed[i]) {
      pressCombo(keyCombos[i]);
    }
    wasPressed[i] = pressed;
  }
  delay(5);
}

void readSerialCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialLine.length() > 0) {
        handleCommand(serialLine);
        serialLine = "";
      }
    } else if (serialLine.length() < 95) {
      serialLine += c;
    }
  }
}

void runEncoderAction(const String &event) {
  int index = encoderEventIndex(event);
  if (index < 0) return;

  String action = encoderActions[index];
  if (action.length() == 0 || action == "NONE") return;
  if (action == "VOLUME_UP") Consumer.write(MEDIA_VOLUME_UP);
  else if (action == "VOLUME_DOWN") Consumer.write(MEDIA_VOLUME_DOWN);
  else if (action == "MUTE") Consumer.write(MEDIA_VOLUME_MUTE);
  else if (action == "MEDIA_NEXT") Consumer.write(MEDIA_NEXT);
  else if (action == "MEDIA_PREV") Consumer.write(MEDIA_PREVIOUS);
  else if (action == "MEDIA_PLAY_PAUSE") Consumer.write(MEDIA_PLAY_PAUSE);
  else if (action == "BRIGHTNESS_UP") Keyboard.press(KEY_F16);
  else if (action == "BRIGHTNESS_DOWN") Keyboard.press(KEY_F17);
  else if (action == "SCROLL_UP") Mouse.move(0, 0, 1);
  else if (action == "SCROLL_DOWN") Mouse.move(0, 0, -1);
  else if (action == "HSCROLL_LEFT") {
    Keyboard.press(KEY_LEFT_SHIFT);
    Mouse.move(0, 0, 1);
    Keyboard.release(KEY_LEFT_SHIFT);
  } else if (action == "HSCROLL_RIGHT") {
    Keyboard.press(KEY_LEFT_SHIFT);
    Mouse.move(0, 0, -1);
    Keyboard.release(KEY_LEFT_SHIFT);
  }
  Keyboard.releaseAll();
  showAction(action);
}

void readEncoder() {
  uint8_t currentState = (digitalRead(ENC_S1) << 1) | digitalRead(ENC_S2);
  static const int8_t transitions[4][4] = {
    {0, 1, -1, 0}, {-1, 0, 0, 1}, {1, 0, 0, -1}, {0, -1, 1, 0}
  };
  int8_t movement = transitions[encoderState][currentState];
  encoderState = currentState;
  if (movement != 0) {
    encoderAccumulator += movement;
    if (encoderAccumulator >= 4) {
      for (uint8_t i = 0; i < encoderSensitivity; i++) runEncoderAction("CW");
      encoderAccumulator = 0;
    } else if (encoderAccumulator <= -4) {
      for (uint8_t i = 0; i < encoderSensitivity; i++) runEncoderAction("CCW");
      encoderAccumulator = 0;
    }
  }

  bool buttonDown = digitalRead(ENC_KEY) == LOW;
  if (buttonDown && !encoderButtonWasDown) encoderButtonAt = millis();
  if (!buttonDown && encoderButtonWasDown && millis() - encoderButtonAt < 800) {
    encoderClickCount++;
    encoderLastClickAt = millis();
  }
  encoderButtonWasDown = buttonDown;
  if (encoderClickCount > 0 && millis() - encoderLastClickAt > 350) {
    if (encoderClickCount > 1) runEncoderAction("DOUBLE_PRESS");
    else emitEncoderEvent("PRESS");
    encoderClickCount = 0;
  }
}

void handleCommand(String command) {
  if (command == "GET_INFO") {
    Serial.println("INFO,ArduinoMacroPad,1.0.0");
    return;
  }

  if (command == "SAVE") {
    saveKeys();
    Serial.println("OK");
    return;
  }

  if (command.startsWith("SET_KEY,")) {
    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);
    int index = command.substring(firstComma + 1, secondComma).toInt();
    if (index >= 1 && index <= KEY_COUNT && secondComma >= 0) {
      String combo = command.substring(secondComma + 1);
      combo.trim();
      bool textMacro = combo.startsWith("TEXT:");
      if (textMacro) {
        combo = "TEXT:" + combo.substring(5);
      } else {
        combo.toUpperCase();
      }
      keyCombos[index - 1] = combo == "NONE" ? "" : combo;
      Serial.println("OK");
    } else {
      Serial.println("ERR,KEY_INDEX");
    }
    return;
  }

  if (command.startsWith("SET_ENCODER,")) {
    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);
    if (secondComma < 0) {
      Serial.println("ERR,ENCODER_EVENT");
      return;
    }
    int index = encoderEventIndex(command.substring(firstComma + 1, secondComma));
    if (index < 0) {
      Serial.println("ERR,ENCODER_EVENT");
      return;
    }
    encoderActions[index] = command.substring(secondComma + 1);
    encoderActions[index].trim();
    Serial.println("OK");
    return;
  }

  if (command.startsWith("SET_SENSITIVITY,")) {
    encoderSensitivity = constrain(command.substring(16).toInt(), 1, 40);
    showAction("Sensitivity " + String(encoderSensitivity));
    Serial.println("OK");
    return;
  }

  if (command.startsWith("SET_PROFILE_NAME,")) {
    profileName = command.substring(17);
    profileName.trim();
    Serial.println("OK");
    return;
  }

  Serial.println("ERR,UNKNOWN_COMMAND");
}

void pressCombo(String combo) {
  if (combo.length() == 0) {
    return;
  }

  if (combo.startsWith("TEXT:")) {
    Keyboard.print(combo.substring(5));
    delay(30);
    Keyboard.releaseAll();
    return;
  }

  String text = combo;
  String normalized = combo;
  normalized.toUpperCase();

  if (normalized.indexOf('+') < 0 && normalized.length() > 1 &&
      !isNamedKey(normalized)) {
    Keyboard.print(text);
    delay(30);
    Keyboard.releaseAll();
    return;
  }

  combo = normalized;
  int start = 0;
  while (start < combo.length()) {
    int end = combo.indexOf('+', start);
    if (end < 0) {
      end = combo.length();
    }

    String token = combo.substring(start, end);
    token.trim();
    pressToken(token);
    delay(20);
    start = end + 1;
  }

  delay(40);
  Keyboard.releaseAll();
}

bool isNamedKey(const String &token) {
  return token == "FN" || token == "CTRL" || token == "CONTROL" || token == "SHIFT" ||
         token == "ALT" || token == "GUI" || token == "WIN" ||
         token == "CMD" || token == "ENTER" || token == "RETURN" ||
         token == "TAB" || token == "ESC" || token == "ESCAPE" ||
         token == "SPACE" || token == "BACKSPACE" || token == "DELETE" ||
         token == "INSERT" || token == "HOME" || token == "END" ||
         token == "LEFT" || token == "RIGHT" || token == "UP" || token == "DOWN" ||
         token == "PAGEUP" || token == "PAGEDOWN" || token == "CAPSLOCK" ||
         token == "NUMLOCK" || token == "SCROLLLOCK" || token == "PAUSE" ||
         token == "MENU" || token == "PLUS" ||
         token == "PRTSC" ||
         (token.charAt(0) == 'F' && token.substring(1).toInt() >= 1 &&
          token.substring(1).toInt() <= 24);
}

void pressToken(const String &token) {
  if (token == "FN") {
  } else if (token == "CTRL" || token == "CONTROL") {
    Keyboard.press(KEY_LEFT_CTRL);
  } else if (token == "SHIFT") {
    Keyboard.press(KEY_LEFT_SHIFT);
  } else if (token == "ALT") {
    Keyboard.press(KEY_LEFT_ALT);
  } else if (token == "GUI" || token == "WIN" || token == "CMD") {
    Keyboard.press(KEY_LEFT_GUI);
  } else if (token == "ENTER" || token == "RETURN") {
    Keyboard.press(KEY_RETURN);
  } else if (token == "TAB") {
    Keyboard.press(KEY_TAB);
  } else if (token == "ESC" || token == "ESCAPE") {
    Keyboard.press(KEY_ESC);
  } else if (token == "SPACE") {
    Keyboard.press(' ');
  } else if (token == "BACKSPACE") {
    Keyboard.press(KEY_BACKSPACE);
  } else if (token == "DELETE") {
    Keyboard.press(KEY_DELETE);
  } else if (token == "INSERT") {
    Keyboard.press(KEY_INSERT);
  } else if (token == "HOME") {
    Keyboard.press(KEY_HOME);
  } else if (token == "END") {
    Keyboard.press(KEY_END);
  } else if (token == "LEFT") {
    Keyboard.press(KEY_LEFT_ARROW);
  } else if (token == "RIGHT") {
    Keyboard.press(KEY_RIGHT_ARROW);
  } else if (token == "UP") {
    Keyboard.press(KEY_UP_ARROW);
  } else if (token == "DOWN") {
    Keyboard.press(KEY_DOWN_ARROW);
  } else if (token == "PAGEUP") {
    Keyboard.press(KEY_PAGE_UP);
  } else if (token == "PAGEDOWN") {
    Keyboard.press(KEY_PAGE_DOWN);
  } else if (token == "CAPSLOCK") {
    Keyboard.press(KEY_CAPS_LOCK);
  } else if (token == "NUMLOCK") {
    Keyboard.press(KEY_NUM_LOCK);
  } else if (token == "SCROLLLOCK") {
    Keyboard.press(KEY_SCROLL_LOCK);
  } else if (token == "PAUSE") {
    Keyboard.press(KEY_PAUSE);
  } else if (token == "MENU") {
    Keyboard.press(KEY_MENU);
  } else if (token == "PLUS") {
    Keyboard.press('+');
  } else if (token == "F1") {
    Keyboard.press(KEY_F1);
  } else if (token == "F2") {
    Keyboard.press(KEY_F2);
  } else if (token == "F3") {
    Keyboard.press(KEY_F3);
  } else if (token == "F4") {
    Keyboard.press(KEY_F4);
  } else if (token == "F5") {
    Keyboard.press(KEY_F5);
  } else if (token == "F6") {
    Keyboard.press(KEY_F6);
  } else if (token == "F7") {
    Keyboard.press(KEY_F7);
  } else if (token == "F8") {
    Keyboard.press(KEY_F8);
  } else if (token == "F9") {
    Keyboard.press(KEY_F9);
  } else if (token == "F10") {
    Keyboard.press(KEY_F10);
  } else if (token == "F11") {
    Keyboard.press(KEY_F11);
  } else if (token == "F12") {
    Keyboard.press(KEY_F12);
  } else if (token == "F13") {
    Keyboard.press(KEY_F13);
  } else if (token == "F14") {
    Keyboard.press(KEY_F14);
  } else if (token == "F15") {
    Keyboard.press(KEY_F15);
  } else if (token == "F16") {
    Keyboard.press(KEY_F16);
  } else if (token == "F17") {
    Keyboard.press(KEY_F17);
  } else if (token == "F18") {
    Keyboard.press(KEY_F18);
  } else if (token == "F19") {
    Keyboard.press(KEY_F19);
  } else if (token == "F20") {
    Keyboard.press(KEY_F20);
  } else if (token == "F21") {
    Keyboard.press(KEY_F21);
  } else if (token == "F22") {
    Keyboard.press(KEY_F22);
  } else if (token == "F23") {
    Keyboard.press(KEY_F23);
  } else if (token == "F24") {
    Keyboard.press(KEY_F24);
  } else if (token == "PRTSC") {
    Keyboard.press(KEY_PRINTSCREEN);
  } else if (token.length() == 1) {
    char key = token.charAt(0);
    if (key >= 'A' && key <= 'Z') {
      key = key - 'A' + 'a';
    }
    Keyboard.press(key);
  }
}