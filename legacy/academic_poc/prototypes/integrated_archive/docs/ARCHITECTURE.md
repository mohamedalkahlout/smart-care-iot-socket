# معمارية النظام المتكامل (System Architecture)
## SmartCare Multi-Socket IoT Hub

منظومة موزع المقابس الذكية المتكاملة مبنية على مبدأ **«الأمان أولاً (Safety-First Architecture)»** مع استقلالية تامة للحافة (Offline-First Autonomy) وإدارة متعددة القنوات للأحمال الكهربائية المنزلية.

---

## 1. مخطط المعمارية الشامل (Architecture Diagram)

```mermaid
graph TD
    subgraph "سحابة Firebase (Unified Cloud)"
        F_RTDB[("Firebase Realtime Database\nmohamednael-467e0")]
        F_RULES["Security Rules (database.rules.json)\nStrict Type & Range Validation"]
        F_RTDB --- F_RULES
    end

    subgraph "لوحة تحكم الويب (Caregiver Web App)"
        WEB_UI["لوحة التحكم المتجاوبة (app/index.html)"]
        WEB_JS["محرك التزامن (app.js)"]
        WEB_EMG["زر إيقاف الطوارئ الشامل (Master All-Off)"]
        WEB_UI --- WEB_JS
        WEB_UI --- WEB_EMG
    end

    subgraph "طبقة البرمجيات المدمجة على ESP32 (Firmware Layer)"
        WIFI_MGR["مدير اتصال WiFi / وضع عدم الاتصال"]
        MAIN_LOOP["المحرك الرئيسي (main.cpp)"]
        NVS["ذاكرة التفضيلات غير المتطايرة (Preferences/NVS)"]
        
        subgraph "حارس الأمان الفيزيائي الصارم (Safety Guard)"
            SG_CORE["حارس الأمان C (safety_guard.c)\nZero-Heap / Non-Negotiable Rules"]
            SG_RULES["قواعد الأمان:\n- قطع الحرارة المطلق\n- سقف تشغيل السخان 120 د\n- سقف تشغيل المضخة 20 د\n- تبريد المضخة 5 د\n- تأخير ضاغط التكييف 3 د\n- إيقاف الطوارئ الشامل"]
            SG_CORE --- SG_RULES
        end

        subgraph "منطق التحكم والتنبؤ (Control & Prediction)"
            CTRL["منطق التبديل والـ Hysteresis (control_logic.c)"]
            NLMS["النموذج التكيفي الخفيف (thermal_model.c)"]
        end

        MAIN_LOOP --> SG_CORE
        MAIN_LOOP --> CTRL
        MAIN_LOOP --> NLMS
        MAIN_LOOP --- NVS
        WIFI_MGR --- MAIN_LOOP
    end

    subgraph "المكونات الفيزيائية (Hardware & Actuators)"
        DHT["مستشعر DHT22 (الحرارة والرطوبة - GPIO 15)"]
        BTN_EMG["زر الطوارئ الفيزيائي (GPIO 4)"]
        LED_ST["مؤشر الحالة (GPIO 13)"]
        RELAY1["قناة 1: سخان / مبرد حراري (GPIO 2)"]
        RELAY2["قناة 2: مضخة المياه / ماتور (GPIO 18)"]
        RELAY3["قناة 3: التلفاز ومحطة العمل (GPIO 19)"]
        RELAY4["قناة 4: التكييف / ضاغط تبريد (GPIO 21)"]
    end

    F_RTDB <==>|HTTP GET / PUT Polling| WIFI_MGR
    WEB_JS <==>|REST Realtime Sync| F_RTDB
    DHT --> MAIN_LOOP
    BTN_EMG --> SG_CORE
    SG_CORE ==>|Enforced Safe Output| RELAY1
    SG_CORE ==>|Enforced Safe Output| RELAY2
    SG_CORE ==>|Enforced Safe Output| RELAY3
    SG_CORE ==>|Enforced Safe Output| RELAY4
    MAIN_LOOP --> LED_ST
```

---

## 2. مصفوفة وظائف القنوات الأربعة (Channel Specifications)

| القناة | نوع الحمل الكهربائي | دبوس GPIO | القواعد الإلزامية لحارس الأمان | السلوك عند انقطاع الإنترنت |
|---|---|---|---|---|
| **قناة 1 (Thermal)** | سخان حراري / مبرد | GPIO 2 | - قطع فوري عند $\ge 45$°م.<br>- سقف تشغيل مستمر 120 دقيقة.<br>- إغلاق فوري عند عطل المستشعر. | يستمر بالتحكم التلقائي الذاتي عبر قراءات DHT22 المحلية. |
| **قناة 2 (Water Pump)** | ماتور مياه حثي | GPIO 18 | - سقف تشغيل مستمر 20 دقيقة منعاً للاحتراق وفيضان الخزان.<br>- فترة سكون إجبارية 5 دقائق قبل إعادة التشغيل. | يحتفظ بآخر حالة آمنة ويقفل تلقائياً عند استنفاد المؤقت. |
| **قناة 3 (Appliance)** | تلفاز / شاشات / أجهزة ترفيهية | GPIO 19 | - إيقاف تلقائي بعد 4 ساعات للقضاء على هدر الاستعداد (Vampire Drain). | يظل خاضعاً للمؤقت الداخلي المحلي. |
| **قناة 4 (AC / Inductive)** | مكيف هواء / ضاغط | GPIO 21 | - تأخير إلزامي للضاغط 180 ثانية (Anti-Short-Cycle) لمنع القفل الميكانيكي.<br>- نطاق Hysteresis $\pm 0.5$°م. | يستمر بالتبريد الذاتي ضمن النطاق المحفوظ في NVS. |

---

## 3. مبدأ عزل طبقة الأمان (Safety Decoupling)
تم تصميم كود `safety_guard.c` بلغة ANSI C الصرفة دون استخدام:
- أي دوال حجز ديناميكي للذاكرة (`malloc` / `free`).
- أي مكتبات شبكية أو بروتوكولات سحابية.
- أي مؤشرات غير مفحوصة (NULL-checked bounds).
هذا يضمن أن قرار الأمان مستقل تماماً عن نجاح أو فشل طبقة الاتصال بالشبكة.
