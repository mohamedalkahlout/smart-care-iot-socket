"""
Notifications Service for Caregivers (P2.4).
Supports bilingual alerts (Arabic and English) with smart debouncing.
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AlertMessage:
    timestamp: float
    event_type: str
    severity: str  # "INFO", "WARNING", "CRITICAL"
    title_ar: str
    body_ar: str
    title_en: str
    body_en: str


class NotificationsService:
    def __init__(self, debounce_window_sec: int = 300):
        self.debounce_window_sec = debounce_window_sec
        self.last_alert_times: Dict[str, float] = {}
        self.sent_alerts: List[AlertMessage] = []

    def should_send(self, event_type: str) -> bool:
        now = time.time()
        last_time = self.last_alert_times.get(event_type, 0)
        if (now - last_time) >= self.debounce_window_sec:
            self.last_alert_times[event_type] = now
            return True
        return False

    def notify_guard_lock(self, device_id: str, reason_code: str, temp_c: float) -> Optional[AlertMessage]:
        event_type = f"guard_lock_{device_id}_{reason_code}"
        if not self.should_send(event_type):
            return None

        alert = AlertMessage(
            timestamp=time.time(),
            event_type=event_type,
            severity="CRITICAL",
            title_ar="⚠️ تدخل حارس الأمان",
            body_ar=f"قام حارس الأمان بإيقاف المقبس ({device_id}) لحماية المنشأة. السبب: {reason_code} (الحرارة: {temp_c:.1f}°م)",
            title_en="⚠️ Safety Guard Intervention",
            body_en=f"Safety Guard stopped socket ({device_id}) for protection. Reason: {reason_code} (Temp: {temp_c:.1f} C)"
        )
        self.sent_alerts.append(alert)
        return alert

    def notify_fridge_anomaly(self, device_id: str, current_temp: float) -> Optional[AlertMessage]:
        event_type = f"fridge_anomaly_{device_id}"
        if not self.should_send(event_type):
            return None

        alert = AlertMessage(
            timestamp=time.time(),
            event_type=event_type,
            severity="WARNING",
            title_ar="❄️ تحذير: ارتفاع حرارة الثلاجة",
            body_ar=f"حرارة الثلاجة مرتفعة ({current_temp:.1f}°م). يرجى التأكد من إغلاق الباب أو سلامة الضاغط.",
            title_en="❄️ Refrigerator Warning",
            body_en=f"Refrigerator temperature is elevated ({current_temp:.1f} C). Please check door closure or compressor health."
        )
        self.sent_alerts.append(alert)
        return alert

    def notify_device_offline(self, device_id: str, offline_minutes: int) -> Optional[AlertMessage]:
        event_type = f"offline_{device_id}"
        if not self.should_send(event_type):
            return None

        alert = AlertMessage(
            timestamp=time.time(),
            event_type=event_type,
            severity="WARNING",
            title_ar="📡 تنبيه: انقطاع الاتصال بالمقبس",
            body_ar=f"المقبس ({device_id}) غير متصل منذ {offline_minutes} دقيقة. الجهاز مستمر بالعمل في وضعه المحلي الآمن.",
            title_en="📡 Socket Disconnection Alert",
            body_en=f"Socket ({device_id}) has been offline for {offline_minutes} minutes. Device continues operating in local safe mode."
        )
        self.sent_alerts.append(alert)
        return alert
