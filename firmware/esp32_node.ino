/*
 * EcoNexo — nodo sensor ESP32 (Edge Computing).
 * Lee DHT11 (temp + humedad) y MQ-4 (gas/metano, proxy de humo) y publica
 * telemetria por MQTT al broker de EcoNexo. Listo para flashear.
 *
 * Topics:
 *   econexo/{ORG_ID}/{DEVICE_ID}/telemetry  -> { "temp","humidity","mq4","battery","rssi" }
 *   econexo/{ORG_ID}/{DEVICE_ID}/status     -> { "online": true }  (LWT: online=false)
 *
 * Librerias (Library Manager): PubSubClient, DHT sensor library, ArduinoJson.
 * Hardware: DHT11 -> GPIO4 ; MQ-4 AOUT -> GPIO34 (ADC1).
 */
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ---- Config (ajustar) ----
const char* WIFI_SSID   = "TU_WIFI";
const char* WIFI_PASS   = "TU_PASSWORD";
const char* MQTT_HOST   = "192.168.0.100";   // IP del broker Mosquitto
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "dev-for-01";        // credencial generada al dar de alta el nodo
const char* MQTT_PASS   = "REEMPLAZAR";        // mostrada una sola vez por el API
const char* ORG_ID      = "REEMPLAZAR_ORG_UUID";
const char* DEVICE_ID   = "for-01";            // external_id

#define DHTPIN   4
#define DHTTYPE  DHT11
#define MQ4_PIN  34

DHT dht(DHTPIN, DHTTYPE);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char topicTelemetry[96];
char topicStatus[96];
unsigned long lastPublish = 0;
const unsigned long PUBLISH_MS = 10000;

void buildTopics() {
  snprintf(topicTelemetry, sizeof(topicTelemetry), "econexo/%s/%s/telemetry", ORG_ID, DEVICE_ID);
  snprintf(topicStatus, sizeof(topicStatus), "econexo/%s/%s/status", ORG_ID, DEVICE_ID);
}

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
}

void connectMqtt() {
  while (!mqtt.connected()) {
    // Last Will: si el nodo cae, el broker publica online=false.
    if (mqtt.connect(DEVICE_ID, MQTT_USER, MQTT_PASS, topicStatus, 1, true, "{\"online\":false}")) {
      mqtt.publish(topicStatus, "{\"online\":true}", true);
    } else {
      delay(3000);
    }
  }
}

float readMQ4() {
  int raw = analogRead(MQ4_PIN);            // 0..4095
  return (raw / 4095.0) * 1000.0;           // aprox. a ppm (calibrar en campo)
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  analogReadResolution(12);
  buildTopics();
  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_MS) {
    lastPublish = millis();
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    float mq4 = readMQ4();
    if (isnan(t) || isnan(h)) return;

    StaticJsonDocument<160> doc;
    doc["temp"] = t;
    doc["humidity"] = h;
    doc["mq4"] = mq4;
    doc["battery"] = 100.0;                  // reemplazar por lectura de bateria real
    doc["rssi"] = WiFi.RSSI();
    char buf[192];
    size_t n = serializeJson(doc, buf);
    mqtt.publish(topicTelemetry, buf, n);
  }
}
