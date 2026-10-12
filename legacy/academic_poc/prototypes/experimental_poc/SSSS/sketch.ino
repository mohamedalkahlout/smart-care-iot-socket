#include <WiFi.h>
#include "DHT.h"
#include <HTTPClient.h>

// ---------- إعدادات بسيطة ----------
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

#define DHTPIN 15
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// نستخدم LED كمؤشر بدلاً من ريليه (مشروع تجريبي)
#define ACT_PIN 2
const int ACT_ON = HIGH;
const int ACT_OFF = LOW;

// رابط نقطة النهاية في Firebase (نقطة socket1 كاملة)
                              
const String DATABASE_URL = "https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1.json";

// نخزن آخر حالة محلياً لتقليل طلبات الكتابة غير الضرورية
String lastStatus = ""; // "on" أو "off"

// ---------- دوال HTTP بسيطة ----------
String httpGET(const String &url) {
  HTTPClient http;
  http.begin(url);
  int code = http.GET();
  String payload = "{}";
  if (code == 200) payload = http.getString();
  http.end();
  return payload;
}

void httpPUT(const String &url, const String &body) {
  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.PUT(body);
  http.end();
}

// ---------- دوال مساعدة لاستخراج حقول من JSON النصي (خفيفة وبسيطة) ----------
String readStringField(const String &json, const String &key) {
  String pattern = "\"" + key + "\":\"";
  int i = json.indexOf(pattern);
  if (i < 0) return "";
  int s = i + pattern.length();
  int e = json.indexOf("\"", s);
  if (e < 0) return "";
  return json.substring(s, e);
}

float readFloatField(const String &json, const String &key, float defVal) {
  String pattern = "\"" + key + "\":";
  int i = json.indexOf(pattern);
  if (i < 0) return defVal;
  int s = i + pattern.length();
  int e = json.indexOf(",", s);
  if (e == -1) e = json.indexOf("}", s);
  if (e == -1) return defVal;
  return json.substring(s, e).toFloat();
}

// ---------- تطبيق حالة التشغيل (LED) وتحديث status في Firebase عند التغيير ----------
void applyState(const String &state) {
  if (state == "on") digitalWrite(ACT_PIN, ACT_ON);
  else digitalWrite(ACT_PIN, ACT_OFF);

  if (state != lastStatus) {
    // نحدّث فقط إذا تغيّرت لتقليل طلبات HTTP
    httpPUT("https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1/status.json",
           "\"" + state + "\"");
    lastStatus = state;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(ACT_PIN, OUTPUT);
  digitalWrite(ACT_PIN, ACT_OFF);

  dht.begin();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println(" Connected");

  // قراءة بداية من DB لضبط الحالة الأولية (إن وجدت)
  String init = httpGET(DATABASE_URL);
  String st = readStringField(init, "status");
  if (st != "") {
    lastStatus = st;
    applyState(lastStatus); // يضبط LED ويكتب status إن اختلف (في هذه الحالة lastStatus كان فارغ)
  } else {
    lastStatus = "off";
    applyState(lastStatus);
  }
}




void loop() {
  // جلب بيانات الـ socket1 كاملة (mode, status, minTemp, maxTemp)
  String data = httpGET(DATABASE_URL);

  // نقرأ الوضع mode و status من الـ DB
  String mode = readStringField(data, "mode"); // "manual" أو "auto" أو ""
  String statusFromDB = readStringField(data, "status"); // "on" أو "off" أو ""

  // قراءة حدود الحرارة (قيم افتراضية لو غير موجودة)
  float minT = readFloatField(data, "minTemp", 20.0);
  float maxT = readFloatField(data, "maxTemp", 30.0);

  if (mode == "manual") {
    // تنفيذ ما في DB (المستخدم يتحكم بالداشبورد)
    if (statusFromDB == "on") applyState("on");
    else applyState("off");
    delay(500);
    return;
  }

  // وضع "auto": نقرأ المستشعر ونقرّر
  float temp = dht.readTemperature();
  if (isnan(temp)) {
    Serial.println("DHT read failed");
    delay(1000);
    return;
  }

  // نكتب currentTemp في الـ DB (حتى يعرضه الداشبورد)
  httpPUT("https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1/currentTemp.json",
         String(temp));

  // قرار التشغيل: داخل النطاق => on ، خارج النطاق => off
  String expected = (temp >= minT && temp <= maxT) ? "on" : "off";
  applyState(expected);

  Serial.printf("Temp=%.2f  min=%.1f max=%.1f state=%s\n", temp, minT, maxT, expected.c_str());
  delay(1000);
}
