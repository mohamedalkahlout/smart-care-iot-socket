# محتوى إطلاق المشروع (LAUNCH_POSTS.md)

---

## 1. منشور لينكدإن (باللغة العربية) 🚀

> 🛡️ **يسعدني إطلاق مشروع «المقبس الذكي الآمن» (Smart Care Socket) كمصدر مفتوح بالكامل!**
>
> بدأت فكرة المشروع من حاجة حقيقية وملحة: كيف يمكن لمقدمي الرعاية ومَن هم خارج المنزل مساعدة كبار السن والأطفال في التحكم بالأجهزة الحرارية (سخانات، مبردات، ثلاجات) دون تعريضهم لمخاطر الحريق أو تلف الأجهزة عند انقطاع الإنترنت أو فشل الحساسات؟
>
> في هذا المشروع الأكاديمي، أعدنا بناء المعمارية البرمجية بالكامل لتكون **«الأمان أولاً (Safety-First Architecture)»**:
>
> 🔹 **حارس أمان برمجي صلب (`Safety Guard`) بلغة C (ANSI C):** معزول تمامًا عن بروتوكولات الشبكة، ويفرض سقف تشغيل مستمر، وقطعًا تلقائيًا عند ارتفاع الحرارة، وفشلًا آمنًا عند انقطاع الحساس، وحماية ضد الدورة القصيرة للضاغط.  
> 🔹 **استقلالية محلية تامة (Offline-First):** الجهاز يتخذ قراراته محليًا ويحفظ إعداداته في ذاكرة NVS ولا يتأثر بانقطاع الإنترنت.  
> 🔹 **ذكاء اصطناعي خفيف على الحافة (Edge NLMS):** نموذج تكيفي خفيف (ذاكرة 24 بايت فقط) حقق في محاكاة غرفة (1R-1C) خفضًا لدورات تبديل الريليه بنسبة **68.4%** لكل 5 أيام وقلص وقت الخروج عن نطاق الراحة بنسبة **11.5%**.  
> 🔹 **لوحة ويب ميسرة لمقدم الرعاية:** متوافقة مع معايير الوصول (WCAG AA) وتتيح الإطفاء الفوري للطوارئ بنقرة واحدة.
>
> ⚠️ **شفافية علمية:** النتائج مقاسة على محاكاة حرارية اصطناعية ونموذج غرفة مكافئ، ومفصلة بالكامل في `docs/EVALUATION.md`. المشروع متاح بالكامل تحت رخصة **Apache 2.0**.
>
> 🔗 رابط المستودع: [رابط المستودع على GitHub]  
> يسعدني سماع آرائكم واقتراحاتكم لتطوير المشروع وخدمة المجتمع!
>
> #IoT #EmbeddedSystems #ESP32 #OpenSource #SafetyEngineering #AssistiveTech #CleanTech

---

## 2. LinkedIn Launch Post (English) 🌍

> 🛡️ **Excited to open-source the Smart Care Socket project!**
>
> Controlling thermal household appliances (space heaters, coolers, refrigerators) remotely for vulnerable occupants—such as seniors and young children—poses critical safety challenges: fire risks, compressor stall, and uncontrolled operation during sensor or network outages.
>
> To address this, we developed a **Safety-First Retrofit Smart Socket** architecture designed for low-cost ESP32 microcontrollers:
>
> 🔹 **Hardware-Decoupled Safety Guard (Pure ANSI C):** Enforces hard non-negotiable safety bounds (max continuous runtime, thermal over-temperature cutoff, sensor stale fail-safes, and compressor anti-short-cycling) independently from network libraries.  
> 🔹 **Resilient Offline-First Autonomy:** Decisions are executed locally with NVS non-volatile persistence—ensuring full operation even during total internet disconnection.  
> 🔹 **Lightweight Edge AI (Adaptive NLMS):** Runs on-device in under 24 bytes of RAM, achieving a **68.4% reduction in relay switching chatter** and an **11.5% decrease in comfort violation time** in 5-day thermal room simulations.  
> 🔹 **Accessible Caregiver Web Dashboard:** WCAG AA compliant with bilingual Arabic/English support and an instant 1-click emergency shutdown button.
>
> 📦 Fully open-source under the **Apache 2.0 license**, accompanied by 60 days of synthetic telemetry, a thermal room simulator, and rigorous unit & C-conformance test suites. (All experimental limits and noise stress-tests documented in `docs/EVALUATION.md`).
>
> 🔗 GitHub Repository: [Your GitHub URL]  
> Looking forward to your feedback and contributions!
>
> #IoT #Firmware #ESP32 #SafetyEngineering #OpenSource #AssistiveTechnology
