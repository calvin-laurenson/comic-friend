#include <Arduino.h>
#include <ArduinoJson.h>
#include <AceButton.h>
using namespace ace_button;

const int LED_PINS[4] = {18, 19, 20, 21};

const int BUTTON_PINS[4] = {10, 11, 12, 13};

AceButton buttons[4];

bool disabled = false;

// Define the maximum size of the JSON message
const size_t JSON_BUFFER_SIZE = JSON_OBJECT_SIZE(3);

// Create a buffer to store the JSON message
StaticJsonDocument<JSON_BUFFER_SIZE> jsonBuffer;

unsigned long previousMillis = 0;
const unsigned long interval = 500;

void handleButtonPress(AceButton *, uint8_t, uint8_t);

void setup()
{
  Serial.begin(9600);

  // Set the LED pins as outputs
  for (int i = 0; i < 4; i++)
  {
    pinMode(LED_PINS[i], OUTPUT);
  }
  // Setup the buttons
  for (int i = 0; i < 4; i++)
  {
    pinMode(BUTTON_PINS[i], INPUT_PULLDOWN);
    buttons[i].init(BUTTON_PINS[i], PinStatus::LOW, i + 1);
    buttons[i].setEventHandler(handleButtonPress);
  }
  ButtonConfig *buttonConfig = ButtonConfig::getSystemButtonConfig();
  buttonConfig->setClickDelay(500);
  // buttonConfig->setDebounceDelay(50);
  // digitalWrite(LED_PINS[0], HIGH);
}

void loop()
{
  if (Serial.available())
  {
    // Read the JSON message from the serial port
    String jsonMessage = Serial.readStringUntil('\n');

    // Clear the JSON buffer
    jsonBuffer.clear();

    // Deserialize the JSON message
    DeserializationError error = deserializeJson(jsonBuffer, jsonMessage);

    // Test if parsing succeeds.
    if (error)
    {
      // Serial.print(F("deserializeJson() failed: "));
      // Serial.println(error.c_str());
      // return;
    }

    // Extract values
    disabled = jsonBuffer["disabled"];
    if (!disabled)
    {
      // Turn off LED 4
      digitalWrite(LED_PINS[3], LOW);
    }
  }
  for (auto i = 0; i < 4; i++)
  {
    buttons[i].check();
  }
  if (disabled)
  {
    // Blink LED 4
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval)
    {
      previousMillis = currentMillis;
      digitalWrite(LED_PINS[3], !digitalRead(LED_PINS[3]));
    }
  }
}

void handleButtonPress(AceButton *button, uint8_t eventType, uint8_t buttonState)
{
  // Serial.println("Button pressed");
  // Get the pin number of the button that was pressed
  int id = button->getId();
  if (!disabled)
  {
    if (buttonState == AceButton::kEventPressed)
    {
      if (id < 4)
      {
        // Turn off all LEDs
        for (int i = 0; i < 3; i++)
        {
          digitalWrite(LED_PINS[i], LOW);
        }
        // Turn on the LED that corresponds to the button that was pressed
        digitalWrite(LED_PINS[id - 1], HIGH);
      }
    }

    if (id == 4)
    {
      // Toggle led
      digitalWrite(LED_PINS[3], !digitalRead(LED_PINS[3]));
    }
    if (id == 4 || buttonState == AceButton::kEventPressed)
    {
      // Create a JSON message
      jsonBuffer.clear();
      JsonObject root = jsonBuffer.to<JsonObject>();
      root["button"] = id;
      root["state"] = buttonState;

      // Serialize the JSON message
      String jsonMessage;
      serializeJson(root, jsonMessage);

      // Send the JSON message through the serial port
      Serial.println(jsonMessage);
    }
  }
}
