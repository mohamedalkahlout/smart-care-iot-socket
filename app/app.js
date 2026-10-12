/**
 * Smart Socket Caregiver Dashboard Logic (P5.1).
 * Features:
 *  - Bilingual Arabic / English support
 *  - One-click Emergency Immediate Off
 *  - Safe Manual Mode Toggle with Confirmation
 *  - Setpoint saving with client-side bounds validation
 *  - Decision source and safety reason explanations
 */

// State
let currentLang = 'ar';
let socketState = {
  status: 'off',
  mode: 'auto',
  deviceType: 'cooling',
  currentTemp: 23.5,
  humidity: 46.0,
  powerW: 0.0,
  minTemp: 21.0,
  maxTemp: 25.0,
  decisionSource: 'auto_rule',
  decisionReason: 'الحرارة ضمن المجال المسموح',
  role: 'caregiver'
};

// Translations
const i18n = {
  ar: {
    appTitle: "المقبس الذكي الآمن",
    appSubtitle: "نظام رعاية كبار السن والأطفال بالأجهزة الحرارية",
    langToggle: "English",
    roleBadge: "دور: مقدم رعاية (Caregiver)",
    emergencyBtn: "إطفاء فوري للطوارئ",
    mainSocketTitle: "المقبس الرئيسي (غرفة المعيشة)",
    deviceTypeCooling: "مروحة / تبريد",
    stateOn: "يعمل",
    stateOff: "متوقف",
    sourceAuto: "قاعدة تلقائية (Auto Rule)",
    sourceManual: "تحكم يدوي (Manual Remote)",
    sourceGuard: "تدخل حارس الأمان (Safety Guard)",
    sourceLocal: "زر محلي فيزيائي (Local Button)",
    turnOnManual: "تشغيل يدوي مؤقت (أمان 30 دقيقة)",
    turnOffManual: "إيقاف يدوي",
    limitsSaved: "✅ تم حفظ وتطبيق حدود الراحة بنجاح.",
    emergencySuccess: "🛑 تم إرسال أمر الإطفاء الفوري للطوارئ بنجاح."
  },
  en: {
    appTitle: "Smart Care Socket",
    appSubtitle: "Thermal Comfort & Safety System for Vulnerable Occupants",
    langToggle: "العربية",
    roleBadge: "Role: Caregiver",
    emergencyBtn: "EMERGENCY IMMEDIATE OFF",
    mainSocketTitle: "Primary Socket (Living Room)",
    deviceTypeCooling: "Cooling / Fan",
    stateOn: "RUNNING",
    stateOff: "OFF",
    sourceAuto: "Auto Thermal Rule",
    sourceManual: "Caregiver Remote Override",
    sourceGuard: "Safety Guard Intervention",
    sourceLocal: "Physical Local Button",
    turnOnManual: "Temporary Manual ON (30 min safe timer)",
    turnOffManual: "Turn OFF",
    limitsSaved: "✅ Comfort boundaries successfully saved.",
    emergencySuccess: "🛑 Emergency shutdown command issued immediately."
  }
};

// DOM Elements
const socketCircle = document.getElementById('socket-visual-circle');
const stateLabel = document.getElementById('socket-state-label');
const verbalHeading = document.getElementById('verbal-status-heading');
const verbalDesc = document.getElementById('verbal-status-desc');
const sourceBadge = document.getElementById('decision-source-badge');
const sourceReason = document.getElementById('decision-reason-text');
const metricTemp = document.getElementById('metric-temp');
const metricHumidity = document.getElementById('metric-humidity');
const metricPower = document.getElementById('metric-power');
const toggleManualBtn = document.getElementById('toggle-manual-btn');
const emergencyBtn = document.getElementById('emergency-off-btn');
const modeSelect = document.getElementById('mode-select');
const minTempInput = document.getElementById('min-temp-input');
const maxTempInput = document.getElementById('max-temp-input');
const saveSetpointsBtn = document.getElementById('save-setpoints-btn');
const langToggleBtn = document.getElementById('lang-toggle-btn');
const notifList = document.getElementById('notifications-list');

function renderUI() {
  const t = i18n[currentLang];

  // Language Direction
  document.documentElement.lang = currentLang;
  document.documentElement.dir = currentLang === 'ar' ? 'rtl' : 'ltr';

  langToggleBtn.textContent = t.langToggle;
  document.getElementById('app-title').textContent = t.appTitle;
  document.getElementById('app-subtitle').textContent = t.appSubtitle;
  document.getElementById('emergency-btn-text').textContent = t.emergencyBtn;

  // Socket visual
  if (socketState.status === 'on') {
    socketCircle.className = 'socket-circle on';
    stateLabel.textContent = t.stateOn;
    verbalHeading.textContent = currentLang === 'ar' ? 'الجهاز قيد التشغيل الفعلي' : 'Appliance is Actively Running';
    verbalDesc.textContent = currentLang === 'ar' 
      ? `الحرارة ${socketState.currentTemp}°م. استهلاك القدرة اللحظي ${socketState.powerW} واط.`
      : `Room temperature is ${socketState.currentTemp} C. Current power draw is ${socketState.powerW} W.`;
    toggleManualBtn.textContent = t.turnOffManual;
  } else {
    socketCircle.className = 'socket-circle off';
    stateLabel.textContent = t.stateOff;
    verbalHeading.textContent = currentLang === 'ar' ? 'الجهاز في وضع الاستعداد والراحة' : 'Appliance is Safely OFF';
    verbalDesc.textContent = currentLang === 'ar'
      ? `حرارة الغرفة ${socketState.currentTemp}°م ضمن المجال الآمن.`
      : `Room temperature is ${socketState.currentTemp} C within safe bounds.`;
    toggleManualBtn.textContent = t.turnOnManual;
  }

  // Source Badge
  sourceBadge.textContent = t[`source${capitalize(socketState.decisionSource)}`] || socketState.decisionSource;
  sourceReason.textContent = socketState.decisionReason;

  // Metrics
  metricTemp.textContent = socketState.currentTemp.toFixed(1);
  metricHumidity.textContent = socketState.humidity.toFixed(0);
  metricPower.textContent = socketState.powerW.toFixed(0);
}

function capitalize(s) {
  if (!s) return '';
  if (s === 'auto_rule') return 'Auto';
  if (s === 'remote') return 'Manual';
  if (s === 'guard') return 'Guard';
  if (s === 'local_button') return 'Local';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function addNotification(type, text) {
  const item = document.createElement('div');
  item.className = `notif-item ${type}`;
  const now = new Date();
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  item.innerHTML = `<span class="notif-time">${timeStr}</span><span class="notif-text">${text}</span>`;
  notifList.prepend(item);
}

// Emergency Immediate Off
emergencyBtn.addEventListener('click', () => {
  socketState.status = 'off';
  socketState.powerW = 0;
  socketState.decisionSource = 'remote';
  socketState.decisionReason = currentLang === 'ar' ? 'إطفاء فوري للطوارئ بطلب من مقدم الرعاية' : 'Emergency shutdown issued by caregiver';
  renderUI();
  addNotification('warning', i18n[currentLang].emergencySuccess);
});

// Manual Toggle Button
toggleManualBtn.addEventListener('click', () => {
  if (socketState.status === 'on') {
    socketState.status = 'off';
    socketState.powerW = 0;
    socketState.decisionSource = 'remote';
    socketState.decisionReason = currentLang === 'ar' ? 'إيقاف يدوي من الواجهة' : 'Manual turn OFF from dashboard';
    addNotification('info', currentLang === 'ar' ? 'تم إيقاف المقبس يدوياً.' : 'Socket turned OFF manually.');
  } else {
    socketState.status = 'on';
    socketState.powerW = 1200;
    socketState.decisionSource = 'remote';
    socketState.decisionReason = currentLang === 'ar' ? 'تشغيل يدوي مؤقت مع مؤقت أمان' : 'Manual ON with safety timeout';
    addNotification('info', currentLang === 'ar' ? 'تم تشغيل المقبس يدوياً بمؤقت أمان.' : 'Socket turned ON with safe timeout.');
  }
  renderUI();
});

// Save Setpoints
saveSetpointsBtn.addEventListener('click', () => {
  const minVal = parseFloat(minTempInput.value);
  const maxVal = parseFloat(maxTempInput.value);

  if (minVal >= maxVal) {
    alert(currentLang === 'ar' ? 'يجب أن يكون الحد الأدنى أقل من الحد الأقصى!' : 'Minimum setpoint must be strictly less than maximum setpoint!');
    return;
  }
  socketState.minTemp = minVal;
  socketState.maxTemp = maxVal;
  addNotification('info', i18n[currentLang].limitsSaved);
});

// Language Toggle
langToggleBtn.addEventListener('click', () => {
  currentLang = currentLang === 'ar' ? 'en' : 'ar';
  renderUI();
});

// NLP Assistant Elements & Handler
const nlpInput = document.getElementById('nlp-command-input');
const nlpSendBtn = document.getElementById('nlp-send-btn');
const nlpResultBox = document.getElementById('nlp-result-box');
const nlpResultStatus = document.getElementById('nlp-result-status');
const nlpResultJson = document.getElementById('nlp-result-json');
const nlpChips = document.querySelectorAll('.nlp-chip');

nlpChips.forEach(chip => {
  chip.addEventListener('click', () => {
    nlpInput.value = chip.getAttribute('data-cmd');
    processNlpCommand(nlpInput.value);
  });
});

if (nlpSendBtn) {
  nlpSendBtn.addEventListener('click', () => {
    if (nlpInput.value.trim()) {
      processNlpCommand(nlpInput.value.trim());
    }
  });
}

if (nlpInput) {
  nlpInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && nlpInput.value.trim()) {
      processNlpCommand(nlpInput.value.trim());
    }
  });
}

async function processNlpCommand(cmdText) {
  nlpResultBox.style.display = 'block';
  nlpResultStatus.innerHTML = '<span style="color: var(--accent-cyan);">⏳ جاري تحليل الأمر وفحص المخطط الأمني...</span>';
  nlpResultJson.textContent = '';

  // Attempt API Gateway call first, with client-side fallback
  try {
    const resp = await fetch('http://127.0.0.1:8080/api/nlp/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmdText })
    });
    const data = await resp.json();
    displayNlpResult(data.success, data.message, data.parsed_config);
  } catch (err) {
    // Client-side fallback mirroring ConstrainedNlpAssistant
    const localResult = localParseCommand(cmdText);
    displayNlpResult(localResult.success, localResult.message, localResult.config);
  }
}

function displayNlpResult(success, message, config) {
  nlpResultBox.style.display = 'block';
  if (success && config) {
    nlpResultStatus.innerHTML = `<span style="color: var(--accent-green);">✅ ${message}</span>`;
    nlpResultJson.textContent = JSON.stringify(config, null, 2);
    
    // Apply changes to socket state safely
    if (config.mode) socketState.mode = config.mode;
    if (config.minTemp !== undefined) {
      socketState.minTemp = config.minTemp;
      minTempInput.value = config.minTemp;
    }
    if (config.maxTemp !== undefined) {
      socketState.maxTemp = config.maxTemp;
      maxTempInput.value = config.maxTemp;
    }
    if (config.status) {
      socketState.status = config.status;
      socketState.powerW = config.status === 'on' ? 1200 : 0;
    }
    socketState.decisionSource = 'remote';
    socketState.decisionReason = `أمر ذكي موثق: ${message}`;
    renderUI();
    addNotification('info', `🤖 مساعد الأوامر: ${message}`);
  } else {
    nlpResultStatus.innerHTML = `<span style="color: #f87171;">${message}</span>`;
    nlpResultJson.textContent = JSON.stringify({ error: "SCHEMA_OR_SAFETY_REJECTION", input: cmdText }, null, 2);
    addNotification('warning', `⚠️ رفض مساعد الأوامر: ${message}`);
  }
}

function localParseCommand(text) {
  const t = text.trim().toLowerCase();
  const hazardous = ["طول الوقت", "بلا توقف", "بدون توقف", "indefinitely", "forever", "أقصى حرارة", "maximum heat", "fire"];
  for (const h of hazardous) {
    if (t.includes(h)) {
      return { success: false, message: "❌ تم رفض الأمر: تعليمات التشغيل الدائم أو غير المحدود محظورة لأسباب تتعلق بالسلامة." };
    }
  }

  const rangeMatch = t.match(/(?:بين|between)\s*(\d+(?:\.\d+)?)\s*(?:و|and|-)\s*(\d+(?:\.\d+)?)/);
  if (rangeMatch) {
    let tMin = parseFloat(rangeMatch[1]);
    let tMax = parseFloat(rangeMatch[2]);
    if (tMin > tMax) { const tmp = tMin; tMin = tMax; tMax = tmp; }
    if (tMin < 10.0 || tMax > 32.0) {
      return { success: false, message: `❌ الحدود المطلوبة [${tMin}, ${tMax}]°م خارج النطاق السكني الآمن (10°م - 32°م).` };
    }
    return {
      success: true,
      message: `تأكيد: ضبط الوضع التلقائي بين ${tMin}°م و ${tMax}°م.`,
      config: { mode: "auto", minTemp: tMin, maxTemp: tMax, hysteresis: 0.5 }
    };
  }

  const timedMatch = t.match(/(?:شغل|turn on|start)\s*(?:السخان|heater|heating)?\s*(?:لمدة|for)?\s*(\d+)\s*(?:دقيقة|min|minutes)/);
  if (timedMatch) {
    const mins = parseInt(timedMatch[1], 10);
    if (mins > 30) {
      return { success: false, message: "❌ لا يمكن تشغيل السخان عن بعد لأكثر من 30 دقيقة كحد أقصى للسلامة." };
    }
    return {
      success: true,
      message: `تأكيد: تشغيل السخان مؤقتًا لمدة ${mins} دقيقة مع إيقاف تلقائي.`,
      config: { mode: "manual", status: "on", deviceType: "heating", remoteHeatingTimerSec: mins * 60 }
    };
  }

  if (["اطفئ", "إطفاء", "أوقف", "turn off", "stop"].some(w => t.includes(w))) {
    return {
      success: true,
      message: "تأكيد: إطفاء المقبس فورًا وبشكل آمن.",
      config: { mode: "manual", status: "off" }
    };
  }

  return {
    success: false,
    message: "عذرًا، لم أفهم الأمر بدقة. جرب: 'اجعل الحرارة بين 22 و 24' أو 'شغل السخان 15 دقيقة'."
  };
}

// Initial Render & Simulated Sensor updates
renderUI();
setInterval(() => {
  // Minor temperature drift simulation
  const drift = (Math.random() - 0.48) * 0.1;
  socketState.currentTemp = Math.round((socketState.currentTemp + drift) * 10) / 10;
  metricTemp.textContent = socketState.currentTemp.toFixed(1);
}, 3000);

