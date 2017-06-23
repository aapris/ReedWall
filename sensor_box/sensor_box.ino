/*

  ReedWall's sensor box sketch.
  Copyright Aapo Rista 2017, MIT-license.
  Reads several cheap arduino complatible sensors, bought from ebay and aliexpress.
  Sends sensor data to a MQTT broker.

  Supported sensors are listed below, more sensors can be added easily.
  - BH1750 lux sensor
  - ultrasonic distance sensor
  - PIR motion sensor
  - SSD1306 OLED display

*/

// #define LEFT_SENSOR    // uncomment for left sensor box, keep commented for right
#ifdef LEFT_SENSOR
  #include "settings_left.h"
  // TODO: study how to construct these from "sensor/" + variable + "/lux" in C
  char lux_topic[20] = "sensor/lft/lux";
  char pir_topic[20] = "sensor/lft/pir";
  char ultrasonic_topic[20] = "sensor/lft/usc";
  char alive_topic[20] = "ping/lft";
#else
  #include "settings_right.h"
  char lux_topic[20] = "sensor/rgt/lux";
  char pir_topic[20] = "sensor/rgt/pir";
  char ultrasonic_topic[20] = "sensor/rgt/usc";
  char alive_topic[20] = "ping/rgt";
#endif


#include <Wire.h>
#include <BH1750.h>
#include "SSD1306.h" // alias for `#include "SSD1306Wire.h"`
#include <NewPing.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// Ultrasonic settings
#define TRIGGER_PIN  D7
#define ECHO_PIN     D5
#define MAX_DISTANCE 300

// PIR settings
const byte interruptPin = D3; // If the board is correctly set in Arduino IDE, you can use D1, D2 etc. directly
volatile byte interruptCounter = 0;
int numberOfInterrupts = 0;
int state = 0;

// Initialize wifi, mqtt, sensor and display objects
WiFiClient espClient;
PubSubClient client(espClient);
BH1750 lightMeter(0x23);
NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE);
SSD1306  display(0x3c, D2, D1);

// Sensor variables
float s_lux = 0;
float s_dist = 0;
float old_s_lux = 0;
float old_s_dist = 0;
unsigned long last_ping_time = 0;
String clientId = "ESP8266Client-";

void setup() {

  Serial.begin(115200);
  Serial.println(F("ReedWall Sensor box"));
  Wire.begin(D2, D1);
  randomSeed(micros());
  clientId += String(random(0xffff), HEX);
  // Initialising the UI will init the display too.
  display.init();
  // display.flipScreenVertically();
  display_2row_text("Hello", "ReedWall!");
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  lightMeter.begin(BH1750_CONTINUOUS_LOW_RES_MODE);
  attachInterrupt(digitalPinToInterrupt(interruptPin), handleInterrupt, CHANGE);
}


void loop() {
  if (!client.connected()) {
    // TODO: Set MQTT status indicator: "connecting"
    reconnect();
  }
  client.loop();
  if (millis() - last_ping_time > 10000) {
    last_ping_time = millis();
    client.publish(alive_topic, String(last_ping_time).c_str(), false);
  }
  old_s_lux = s_lux;
  s_lux = lightMeter.readLightLevel();
  old_s_dist = s_dist;
  s_dist = sonar.ping_cm();
  
  Serial.print(millis());
  Serial.print(" Light: ");
  Serial.print(s_lux);
  Serial.print(" lx");
  Serial.print(" distance: ");
  Serial.print(s_dist);
  Serial.println(" cm");
  if (s_lux > 10 && has_changed_enough(old_s_lux, s_lux)) {
    display_3row_text("LUX", "changed", String(s_lux));
    client.publish(lux_topic, String(s_lux).c_str(), false);
  }  
  if (s_dist > 10 && has_changed_enough(old_s_dist, s_dist)) {
    if  (s_dist < 30) {
      display_2row_text("HANDS", "OFF!!!");
    } else {
      display_3row_text("Distance", "changed", String(s_dist));
    }
    client.publish(ultrasonic_topic, String(s_dist).c_str(), false);
  }
  if(interruptCounter>0){
 
      interruptCounter--;
      numberOfInterrupts++;

      client.publish(pir_topic, String(state).c_str(), false);
      Serial.print("Interrupt ");
      if (state == 1) {
        Serial.print(" RISING");
        display_2row_text("Motion", "detected");
      } else {
        Serial.print("FALLING");
      }
      Serial.print(" at ");
      Serial.print(millis());
      Serial.print(" ms uptime. Total: ");      
      Serial.println(numberOfInterrupts);
  }
  
  delay(100);

}


void handleInterrupt() {
  interruptCounter++;
  state = digitalRead(interruptPin);
}


bool has_changed_enough(float val1, float val2) {
  /*
   * If value has changed more than 10% return true
   */
  float ratio;
  if (val1 >= val2) { ratio = val2/val1;}
  else { ratio = val1/val2;}
  // Serial.println(ratio);
  if (ratio < 0.9) {
    return 1;
  } else { 
    return 0;
  }
}


void display_2row_text(String row1, String row2) {
#ifdef has_ssd1306
  display.clear();
  display.setFont(ArialMT_Plain_24);
  display.drawString(0, 0, row1);
  display.drawString(0, 26, row2);
  display.display();
#endif
}

void display_3row_text(String row1, String row2, String row3) {
#ifdef has_ssd1306
  display.clear();
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, row1);
  display.drawString(0, 20, row2);
  display.drawString(0, 40, row3);
  display.display();
#endif
}


void setup_wifi() {
  display_2row_text("Waiting", "for WiFi");
  Serial.println("Wait 5 sec");
  delay(5);
  display_2row_text("Connecting to", wifi_ssid);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(wifi_ssid);

  WiFi.begin(wifi_ssid, wifi_password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  display_2row_text("WiFi connected", wifi_ssid);
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    display_2row_text("Connecting", "broker...");
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    // If you do not want to use a username and password, change next line to
    // if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      display_2row_text("Connected", "to broker...");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

