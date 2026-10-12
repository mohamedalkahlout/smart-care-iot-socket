#include <WiFi.h>
#include "DHT.h"
#include <HTTPClient.h>

// إعدادات الواي فاي
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// إعدادات المستشعر
#define DHTPIN 15
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// إعدادات الريليه
#define RELAY_PIN 2

// ===== إضافات مهمة =====
bool relayActiveHigh = true;    // نكتشفها عند الإقلاع (استرشادي)
String lastStatus = "";         // آخر حالة مسجلة ("on"/"off")
float lastTempSent = -1000.0;   // آخر temp مرسلة
const float TEMP_SEND_DELTA = 0.2; // عتبة إرسال temp لتقليل طلبات DB
// =======================

// رابط Realtime Database (لاحظ .json)
String DATABASE_URL = "https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1.json";

// --------------------- دوال HTTP ---------------------
String httpGETRequest(String url) {
  HTTPClient http;
  http.begin(url);
  http.setReuse(true);

  int httpResponseCode = http.GET();
  String payload = "{}";
  if (httpResponseCode == 200) {
    payload = http.getString();
  } else {
    Serial.printf("⚠️ GET failed, code: %d\n", httpResponseCode);
  }
  http.end();
  return payload;
}

void httpPUTRequest(String url, String jsonPayload) {
  HTTPClient http;
  http.begin(url);
  http.setReuse(true);
  http.addHeader("Content-Type", "application/json");
  int httpResponseCode = http.PUT(jsonPayload);
  if (httpResponseCode > 0) {
    Serial.printf("✅ PUT success (code=%d) URL=%s payload=%s\n", httpResponseCode, url.c_str(), jsonPayload.c_str());
  } else {
    Serial.printf("❌ PUT error: %s  URL=%s payload=%s\n", http.errorToString(httpResponseCode).c_str(), url.c_str(), jsonPayload.c_str());
  }
  http.end();
}
// ----------------------------------------------------

// دالة تكتب على الريليه (مع مراعاة polarity) ثم تفترض النجاح وتحدّث DB فقط لو تغيرت الحالة المسجلة
void setRelayStateIfChanged(const String &wantState) {
  // نحسب القيمة التي سنكتبها على الدبوس (HIGH/LOW) بناءً على polarity
  int writeValue;
  if (wantState == "on") writeValue = relayActiveHigh ? HIGH : LOW;
  else writeValue = relayActiveHigh ? LOW : HIGH;

  // اكتب على الريليه
  digitalWrite(RELAY_PIN, writeValue);

  // امنح الموديول وقتًا للاستقرار
  delay(60);

  // نفترض النجاح؛ الحالة الحقيقية التي نرسلها للـ DB = wanted state
  String realState = wantState;

  // حدث DB فقط لو تغيّرت الحالة المسجلة مسبقًا
  if (realState != lastStatus) {
    String url = "https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1/status.json";
    httpPUTRequest(url, "\"" + realState + "\"");
    lastStatus = realState;
  }
}

// طباعة حالة الريليه مختصرة وواضحة
void printRelayState() {
  Serial.printf("🔌 Relay: %s\n", lastStatus == "on" ? "ON" : "OFF");
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  dht.begin();

  // اتصال الواي فاي
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected");

  // ---- كشف قطبية الريليه (est.) ----
  digitalWrite(RELAY_PIN, HIGH);
  delay(60);
  int readHigh = digitalRead(RELAY_PIN);
  digitalWrite(RELAY_PIN, LOW);
  delay(60);
  int readLow = digitalRead(RELAY_PIN);

  if (readHigh == HIGH && readLow == LOW) {
    relayActiveHigh = true;
    Serial.println("Relay polarity (est): active HIGH");
  } else if (readHigh == LOW && readLow == HIGH) {
    relayActiveHigh = false;
    Serial.println("Relay polarity (est): active LOW");
  } else {
    relayActiveHigh = false;
    Serial.println("Relay polarity (est): ambiguous — assuming active LOW");
  }

  // ----- قراءة الحالة المبدئية من DB وضبط lastStatus -----
  String initData = httpGETRequest(DATABASE_URL);
  Serial.println("initial DB: " + initData);

  int statusIndex = initData.indexOf("\"status\":\"");
  if (statusIndex >= 0) {
    int start = statusIndex + 10;
    int end = initData.indexOf("\"", start);
    lastStatus = initData.substring(start, end);
    Serial.printf("initial lastStatus = %s\n", lastStatus.c_str());

    // ضبط المخرج وفق الحالة المبدئية
    if (lastStatus == "on") digitalWrite(RELAY_PIN, relayActiveHigh ? HIGH : LOW);
    else digitalWrite(RELAY_PIN, relayActiveHigh ? LOW : HIGH);

    delay(100);
  } else {
    Serial.println("initial status not found in DB; reading pin for guess");
    lastStatus = digitalRead(RELAY_PIN) == HIGH ? "on" : "off";
    Serial.printf("initial guess lastStatus=%s\n", lastStatus.c_str());
  }

  // اطبع حالة الريليه عند الإقلاع (دون طباعة حرارة)
  printRelayState();
}

void loop() {
  // جلب DB أولًا (نعرف الوضع: manual/auto وحدود الحرارة)
  String data = httpGETRequest(DATABASE_URL);

  // قراءات mode/status من DB
  bool isManual = data.indexOf("\"mode\":\"manual\"") >= 0;
  // الحصول على statusOn من DB (لكن الحالة الحقيقة نحسبها ونعكسها في lastStatus عبر setRelayStateIfChanged)
  bool dbStatusOn = data.indexOf("\"status\":\"on\"") >= 0;

  if (isManual) {
    // --- وضع يدوي: لا نكتب أو نطبع أي شيء عن المستشعر ---
    // فقط نتأكد من تنفيذ طلب المستخدم (DB قد تحتوي status: "on" أو "off")
    if (dbStatusOn) setRelayStateIfChanged("on");
    else setRelayStateIfChanged("off");

    // طباعة مُبسطة توضح حالة الريليه فقط
    printRelayState();

    // لا نحدث currentTemp في وضع اليدوي — ننتظر تغيّر الوضع
    delay(1000);
    return;
  }

  // --- وضع تلقائي: نقرأ المستشعر ونعرض الحالة والحرارة ---
  float temp = dht.readTemperature();
  if (isnan(temp)) {
    Serial.println("⚠️ DHT read failed");
    delay(1500);
    return;
  }

  // أطبع القراءة دائماً للمستخدم (طلبك)
  Serial.printf("🌡️ currentTemp = %.2f °C\n", temp);

  // إرسال currentTemp إلى DB فقط إذا تغيّر بما يكفي (للحد من طلبات PUT)
  if (isnan(lastTempSent) || fabs(temp - lastTempSent) >= TEMP_SEND_DELTA) {
    httpPUTRequest("https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1/currentTemp.json", String(temp));
    lastTempSent = temp;
    // عند نجاح PUT ستظهر طباعة نجاح داخل httpPUTRequest
  }
  // (ملاحظة: لا نطبع رسالة "لم يتغير" لتفادي الضجيج)

  // استخراج minTemp و maxTemp من JSON
  int minIndex = data.indexOf("\"minTemp\":");
  int maxIndex = data.indexOf("\"maxTemp\":");
  float minTemp = 20.0;
  float maxTemp = 30.0;

  if (minIndex >= 0) {
    int start = minIndex + 10;
    int end = data.indexOf(",", start);
    if (end == -1) end = data.indexOf("}", start);
    minTemp = data.substring(start, end).toFloat();
  }
  if (maxIndex >= 0) {
    int start = maxIndex + 10;
    int end = data.indexOf(",", start);
    if (end == -1) end = data.indexOf("}", start);
    maxTemp = data.substring(start, end).toFloat();
  }

  // حساب الحالة المتوقعة
  String expectedState = (temp >= minTemp && temp <= maxTemp) ? "on" : "off";

  // نفّذ الحالة المتوقعة وحدث DB عند التغيير
  setRelayStateIfChanged(expectedState);

  // اطبع حالة الريليه بعد التنفيذ (واضح وبسّطنا الرسائل)
  printRelayState();

  delay(1000);
}
