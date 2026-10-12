"""
Constrained NLP Rule Assistant (P4.5 / Schema-Enforced).
Smart Care IoT Socket (Retrofit Edge-AI & Safety Guard)

Converts natural language commands (Arabic/English) into strict, validated JSON configs.
Rejects hazardous instructions (e.g., "heat room to 60 C" or "run heater indefinitely").
Enforces a formal JSON schema on all generated command payloads.
"""
import re
from typing import Any, Dict, Optional, Tuple

# Formal JSON Schema Specification for Socket Commands
COMMAND_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SmartSocketCommand",
    "description": "Validated control schema for Smart Care IoT Socket",
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["auto", "manual"]
        },
        "minTemp": {
            "type": "number",
            "minimum": 10.0,
            "maximum": 32.0
        },
        "maxTemp": {
            "type": "number",
            "minimum": 10.0,
            "maximum": 32.0
        },
        "hysteresis": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 3.0
        },
        "status": {
            "type": "string",
            "enum": ["on", "off"]
        },
        "deviceType": {
            "type": "string",
            "enum": ["cooling", "heating", "compressor", "generic"]
        },
        "remoteHeatingTimerSec": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1800  # Max 30 minutes continuous remote heater run
        }
    },
    "required": ["mode"],
    "additionalProperties": False
}


def validate_command_schema(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates that a generated configuration strictly complies with COMMAND_JSON_SCHEMA.
    Zero-dependency pure Python schema validator.
    """
    if not isinstance(config, dict):
        return False, "Payload must be a JSON object"

    # Required properties
    if "mode" not in config or config["mode"] not in ["auto", "manual"]:
        return False, "Property 'mode' is required and must be 'auto' or 'manual'"

    # Check additionalProperties
    allowed_keys = set(COMMAND_JSON_SCHEMA["properties"].keys())
    for k in config.keys():
        if k not in allowed_keys:
            return False, f"Unexpected property '{k}' not permitted in schema"

    # Check value bounds
    if "minTemp" in config:
        val = config["minTemp"]
        if not isinstance(val, (int, float)) or not (10.0 <= val <= 32.0):
            return False, "minTemp must be a float between 10.0 and 32.0 C"

    if "maxTemp" in config:
        val = config["maxTemp"]
        if not isinstance(val, (int, float)) or not (10.0 <= val <= 32.0):
            return False, "maxTemp must be a float between 10.0 and 32.0 C"

    if "minTemp" in config and "maxTemp" in config:
        if config["minTemp"] >= config["maxTemp"]:
            return False, "minTemp must be strictly less than maxTemp"

    if "hysteresis" in config:
        val = config["hysteresis"]
        if not isinstance(val, (int, float)) or not (0.1 <= val <= 3.0):
            return False, "hysteresis must be between 0.1 and 3.0 C"

    if "status" in config and config["status"] not in ["on", "off"]:
        return False, "status must be 'on' or 'off'"

    if "remoteHeatingTimerSec" in config:
        val = config["remoteHeatingTimerSec"]
        if not isinstance(val, int) or not (0 <= val <= 1800):
            return False, "remoteHeatingTimerSec must be integer between 0 and 1800"

    return True, "Schema valid"


class ConstrainedNlpAssistant:
    def __init__(self):
        self.schema = COMMAND_JSON_SCHEMA

    def parse_command(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parses text and returns (is_valid, parsed_json_config, human_readable_summary_or_error).
        Guarantees that any returned parsed_json_config passes validate_command_schema.
        """
        text_clean = text.strip().lower()

        # Check for dangerous hazardous instructions
        hazardous_keywords = [
            "طول الوقت", "بلا توقف", "بدون توقف", "indefinitely", "forever",
            "أقصى حرارة", "maximum heat", "fire", "99", "100"
        ]
        for hk in hazardous_keywords:
            if hk in text_clean:
                return False, None, "❌ تم رفض الأمر: تعليمات التشغيل الدائم أو غير المحدود محظورة لأسباب تتعلق بالسلامة."

        # Pattern 1: Temperature range (e.g. "بين 22 و 24" or "between 20 and 25")
        range_match = re.search(r'(?:بين|between)\s*(\d+(?:\.\d+)?)\s*(?:و|and|-)\s*(\d+(?:\.\d+)?)', text_clean)
        if range_match:
            t_min = float(range_match.group(1))
            t_max = float(range_match.group(2))
            if t_min > t_max:
                t_min, t_max = t_max, t_min

            # Validate physical safety bounds
            if t_min < 10.0 or t_max > 32.0:
                return False, None, f"❌ الحدود المطلوبة [{t_min}, {t_max}]°م خارج النطاق السكني الآمن (10°م - 32°م)."

            config = {
                "mode": "auto",
                "minTemp": t_min,
                "maxTemp": t_max,
                "hysteresis": 0.5,
            }

            # Enforce schema validation
            is_valid, msg = validate_command_schema(config)
            if not is_valid:
                return False, None, f"❌ خطأ في مطابقة المخطط: {msg}"

            summary = f"تأكيد: ضبط الوضع التلقائي بين {t_min}°م و {t_max}°م."
            return True, config, summary

        # Pattern 2: Timed heating (e.g. "شغل السخان 20 دقيقة" or "turn on heater for 25 mins")
        timed_heater = re.search(
            r'(?:شغل|turn on|start)\s*(?:السخان|heater|heating)?\s*(?:لمدة|for)?\s*(\d+)\s*(?:دقيقة|min|minutes)',
            text_clean
        )
        if timed_heater:
            duration_mins = int(timed_heater.group(1))
            if duration_mins > 30:
                return False, None, "❌ لا يمكن تشغيل السخان عن بعد لأكثر من 30 دقيقة كحد أقصى للسلامة."

            config = {
                "mode": "manual",
                "status": "on",
                "deviceType": "heating",
                "remoteHeatingTimerSec": duration_mins * 60,
            }

            is_valid, msg = validate_command_schema(config)
            if not is_valid:
                return False, None, f"❌ خطأ في مطابقة المخطط: {msg}"

            summary = f"تأكيد: تشغيل السخان مؤقتًا لمدة {duration_mins} دقيقة مع إيقاف تلقائي."
            return True, config, summary

        # Pattern 3: Turn off immediately
        if any(w in text_clean for w in ["اطفئ", "إطفاء", "أوقف", "turn off", "stop", "shut down"]):
            config = {
                "mode": "manual",
                "status": "off",
            }
            is_valid, msg = validate_command_schema(config)
            if not is_valid:
                return False, None, f"❌ خطأ في مطابقة المخطط: {msg}"

            summary = "تأكيد: إطفاء المقبس فورًا وبشكل آمن."
            return True, config, summary

        return False, None, "عذرًا، لم أفهم الأمر بدقة. يمكنك صياغته مثل: 'اجعل الحرارة بين 22 و24 درجة' أو 'شغل السخان 15 دقيقة'."

    def process_api_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        API Gateway Handler:
        Takes an API payload {'command': '...'}, runs parse_command,
        and returns a structured, schema-validated JSON response.
        """
        command_text = payload.get("command", "")
        if not command_text:
            return {
                "success": False,
                "error": "Missing 'command' parameter",
                "schema_enforced": True
            }

        valid, config, message = self.parse_command(command_text)
        return {
            "success": valid,
            "command_received": command_text,
            "parsed_config": config,
            "message": message,
            "schema_enforced": True
        }
