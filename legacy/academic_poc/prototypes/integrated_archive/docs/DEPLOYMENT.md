# دليل النشر والإطلاق (DEPLOYMENT.md)
## SmartCare Multi-Socket IoT Hub

يوضح هذا الدليل خطوات إطلاق ونشر المشروع المتكامل على GitHub وإعداد سحابة Firebase الموحدة.

---

## 1. إعداد سحابة Firebase (Unified Account: `mohamednael-467e0`)

1. ادخل إلى [Firebase Console](https://console.firebase.google.com/) وافتح المشروع: `mohamednael-467e0`.
2. انتقل إلى **Realtime Database**.
3. استورد البيانات الأولية من ملف:
   [`cloud/initial_data.json`](../cloud/initial_data.json)
4. في تبويب **Rules (القواعد)**، الصق محتوى ملف قواعد الأمان المحكمة:
   [`cloud/database.rules.json`](../cloud/database.rules.json) ثم اضغط **Publish**.

---

## 2. بناء وبرمجة شريحة ESP32 (Firmware Flashing)

باستخدام PlatformIO:
```bash
cd firmware
pio run -e esp32dev --target upload
pio device monitor -b 115200
```

---

## 3. تشغيل لوحة التحكم (Web Dashboard)

لوحة الويب لا تتطلب خوادم Node.js أو خوادم خلفية معقدة؛ افتح الملف مباشرة في أي متصفح:
```bash
start app/index.html
```
أو ارفع مجلد `app/` مباشرة إلى **GitHub Pages** ليصبح متاحاً للوصول من أي هاتف محمول.

---

## 4. النشر على GitHub (Publishing to GitHub)

المشروع مهيأ تماماً ليكون مستودعاً مستقلاً ونظيفاً على GitHub:
```bash
git init
git add .
git commit -m "feat: Initial release of SmartCare Multi-Socket IoT Safety Hub"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/smartcare-multisocket-hub.git
git push -u origin main
```
