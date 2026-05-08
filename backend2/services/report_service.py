import html
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from openai import OpenAI

try:
    from reportlab.lib import colors  # type: ignore[reportMissingImports]
    from reportlab.lib.pagesizes import A4  # type: ignore[reportMissingImports]
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[reportMissingImports]
    from reportlab.lib.units import cm  # type: ignore[reportMissingImports]
    from reportlab.platypus import (  # type: ignore[reportMissingImports]
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except Exception:
    colors = None  # type: ignore[assignment]
    A4 = None  # type: ignore[assignment]
    ParagraphStyle = None  # type: ignore[assignment]
    getSampleStyleSheet = None  # type: ignore[assignment]
    cm = None  # type: ignore[assignment]
    PageBreak = None  # type: ignore[assignment]
    Paragraph = None  # type: ignore[assignment]
    SimpleDocTemplate = None  # type: ignore[assignment]
    Spacer = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    TableStyle = None  # type: ignore[assignment]

from db.supabase_client import get_supabase_client

REPORTS_DIR = "generated_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

OPENAI_REPORT_MODEL = os.getenv("OPENAI_REPORT_MODEL", "gpt-5.5")
REPORT_WINDOW_DAYS = int(os.getenv("REPORT_WINDOW_DAYS", "5"))

_TECHNICAL_FAILURE_PATTERNS = [
    "agent stopped",
    "iteration limit",
    "traceback",
    "stack trace",
    "exception",
    "timeout",
    "tool error",
    "runtime error",
    "typeerror",
    "attributeerror",
    "valueerror",
    "keyerror",
    "connectionerror",
    "httpexception",
    "internal server error",
    "tool_call",
]

# usable page width — initialised inside build_patient_report_pdf before any builder runs
_PW: Any = None


# ──────────────────────────────────────────────────────────────────────────────
# Guards
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_reportlab_installed() -> None:
    if SimpleDocTemplate is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ReportLab is not installed. Run: pip install reportlab",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Basic helpers
# ──────────────────────────────────────────────────────────────────────────────

def safe_text(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def _esc(text: Any) -> str:
    """Escape arbitrary text for safe use inside ReportLab Paragraph XML."""
    return html.escape(str(text), quote=False) if text else ""


def pick_first(row: dict, keys: tuple, default=None):
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def parse_datetime_safe(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    value = str(value).strip()
    if not value:
        return None
    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Date / time formatters
# ──────────────────────────────────────────────────────────────────────────────

def format_date(value) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.strptime(str(value).strip()[:10], "%Y-%m-%d")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except Exception:
        return str(value)


def _format_hm(hour: int, minute: int) -> str:
    period = "AM" if hour < 12 else "PM"
    display_hour = 12 if hour in (0, 12) else hour % 12
    return f"{display_hour}:{minute:02d} {period}"


def format_time(value) -> str:
    if not value:
        return "-"
    s = str(value).strip()
    # Pure time string like "13:00:00" or "13:00"
    if re.match(r"^\d{1,2}:\d{2}", s) and "T" not in s and not re.match(r"^\d{4}-", s):
        parts = s.split(":")
        try:
            return _format_hm(int(parts[0]), int(parts[1]))
        except Exception:
            pass
    parsed = parse_datetime_safe(s)
    if parsed:
        return _format_hm(parsed.hour, parsed.minute)
    return s


def format_datetime(value) -> str:
    if not value:
        return "-"
    parsed = parse_datetime_safe(value)
    if not parsed:
        return str(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year} at {_format_hm(parsed.hour, parsed.minute)}"


# ──────────────────────────────────────────────────────────────────────────────
# Status helpers
# ──────────────────────────────────────────────────────────────────────────────

def status_display_label(status_val: str, item_type: str = "general") -> str:
    if status_val in ("taken", "confirmed"):
        return {"meal": "Confirmed", "medication": "Taken", "activity": "Completed"}.get(item_type, "Confirmed")
    if status_val == "missed":
        return "Missed"
    return "Unknown"


def status_html_color(status_val: str) -> str:
    return {"taken": "#15803D", "confirmed": "#15803D", "missed": "#DC2626"}.get(status_val, "#B45309")


def evidence_note(status_val: str, item_type: str) -> str:
    if status_val in ("taken", "confirmed"):
        return "Confirmed in conversation"
    if status_val == "missed":
        return "Patient indicated not completed"
    return "No explicit confirmation found"


# ──────────────────────────────────────────────────────────────────────────────
# Conversation helpers
# ──────────────────────────────────────────────────────────────────────────────

def is_failed_assistant_response(text: str) -> bool:
    if not text or not text.strip():
        return True
    tl = text.lower()
    return any(p in tl for p in _TECHNICAL_FAILURE_PATTERNS)


def clean_conversation_text(text: str) -> str:
    return "Response unavailable" if is_failed_assistant_response(text) else text.strip()


_TRIVIAL_PATTERNS = re.compile(
    r"^("
    r"hi+|hello+|hey+|hiya|howdy|greetings|good\s*(morning|afternoon|evening|night|day)|"
    r"how are you|how r u|how do you do|what'?s up|sup|yo|ok|okay|yes|no|thanks|thank you|"
    r"bye|goodbye|see you|later|nice|great|good|fine|cool|alright|sure|please|help|"
    r"hi\s+i'?m?\s+\w+|hello\s+i'?m?\s+\w+|my name is \w+"
    r")[\s!?.]*$",
    re.IGNORECASE,
)

_MEANINGFUL_KEYWORDS = re.compile(
    r"\b(who|what|where|when|why|how|is|are|was|were|do|does|did|can|could|should|would|"
    r"my|me|son|daughter|wife|husband|mother|father|brother|sister|family|doctor|"
    r"medication|medicine|pill|tablet|dose|drug|eat|meal|breakfast|lunch|dinner|food|"
    r"activity|exercise|appointment|name|age|address|remember|forget|today|tomorrow|"
    r"time|date|year|place|live|home)\b",
    re.IGNORECASE,
)


def group_repeated_questions(interactions: list) -> list:
    questions = []
    for row in interactions:
        t = str(pick_first(row, ("user_text", "interaction_text", "message"), "") or "").strip()
        if len(t) < 6 or len(t) > 500:
            continue
        if _TRIVIAL_PATTERNS.match(t):
            continue
        if not _MEANINGFUL_KEYWORDS.search(t):
            continue
        questions.append(t)

    def norm(t: str) -> str:
        return re.sub(r"[^a-z0-9\s]", "", t.lower().strip())

    normalized = [norm(q) for q in questions]
    counts = Counter(normalized)
    result, seen = [], set()
    for q, n in zip(questions, normalized):
        if counts[n] >= 2 and n not in seen:
            seen.add(n)
            result.append({"text": q, "count": counts[n]})
    return sorted(result, key=lambda x: x["count"], reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────

def filter_rows_by_date_window(
    rows: list,
    candidate_keys: tuple,
    days: int,
    include_if_no_date: bool = False,
) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []
    for row in rows:
        parsed = parse_datetime_safe(pick_first(row, candidate_keys, None))
        if parsed is None:
            if include_if_no_date:
                filtered.append(row)
        elif parsed >= cutoff:
            filtered.append(row)
    return filtered


def get_patient_by_id(patient_id: int):
    client = get_supabase_client()
    result = client.table("patients").select("*").eq("patient_id", patient_id).limit(1).execute()
    return result.data[0] if result.data else None


def get_interactions_for_patient(patient_id: int, days: int = REPORT_WINDOW_DAYS, limit: int = 300) -> list:
    client = get_supabase_client()
    result = (
        client.table("interaction_log")
        .select("*")
        .eq("patient_id", patient_id)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    _ts_keys = ("interaction_timestamp", "interaction_time", "created_at", "timestamp", "logged_at")
    rows = filter_rows_by_date_window(rows, _ts_keys, days=days, include_if_no_date=False)
    rows.sort(key=lambda r: pick_first(r, _ts_keys, ""), reverse=True)
    return rows


def try_get_patient_medications(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_medications")
            .select("*, medication(medication_name)")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            if isinstance(row.get("medication"), dict):
                row["medication_name"] = row["medication"].get("medication_name", "-")
            if "medication_time" in row:
                row["scheduled_time"] = row["medication_time"]
        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


def try_get_patient_meals(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_meals")
            .select("*, meals(meal_type)")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            if isinstance(row.get("meals"), dict):
                row["meal_name"] = row["meals"].get("meal_type", "-")
        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


def try_get_patient_activities(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_activities")
            .select("*, activity(activity_type)")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            if isinstance(row.get("activity"), dict):
                row["activity_name"] = row["activity"].get("activity_type", "-")
        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at", "start_time"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Item extraction and status inference
# ──────────────────────────────────────────────────────────────────────────────

def extract_item_name(row: dict, item_type: str) -> str:
    keys = {
        "meal": ("meal_name", "food_name", "item_name", "name", "title"),
        "medication": ("medication_name", "medicine_name", "item_name", "name", "title"),
        "activity": ("activity_name", "item_name", "name", "title"),
    }.get(item_type, ("name",))
    return safe_text(pick_first(row, keys, "-"))


def extract_item_time(row: dict, item_type: str) -> str:
    keys = {
        "meal": ("meal_time", "scheduled_time", "time", "due_time"),
        "medication": ("scheduled_time", "time", "dose_time", "due_time"),
        "activity": ("start_time", "scheduled_time", "time", "due_time"),
    }.get(item_type, ("scheduled_time", "time"))
    return safe_text(pick_first(row, keys, "-"))


def extract_interaction_text(row: dict) -> str:
    user = str(pick_first(row, ("user_text", "interaction_text", "message", "content", "notes"), "") or "")
    assistant = str(pick_first(row, ("assistant_text", "agent_text", "reply", "response"), "") or "")
    return f"{user} {assistant}".lower()


def infer_item_status_from_interactions(item_name: str, interactions: list, item_type: str) -> tuple:
    """Returns (status, evidence_snippet)."""
    item_lower = item_name.strip().lower()
    if not item_lower or item_lower == "-":
        return "unknown", ""

    for row in interactions:
        text = extract_interaction_text(row)
        if item_lower not in text:
            continue

        if item_type == "meal":
            if any(p in text for p in ["did not eat", "didn't eat", "not eaten", "missed", "skipped", "skip"]):
                return "missed", text[:100]
            if any(p in text for p in ["ate", "eaten", "had", "finished", "completed"]):
                return "taken", text[:100]
        elif item_type == "medication":
            if any(p in text for p in ["did not take", "didn't take", "not taken", "missed", "skipped", "skip"]):
                return "missed", text[:100]
            if any(p in text for p in ["took", "taken", "completed", "done"]):
                return "taken", text[:100]
        elif item_type == "activity":
            if any(p in text for p in ["did not do", "didn't do", "not done", "missed", "skipped", "skip"]):
                return "missed", text[:100]
            if any(p in text for p in ["done", "completed", "finished", "performed"]):
                return "taken", text[:100]

    return "unknown", ""


def build_item_summary(rows: list, interactions: list, item_type: str) -> tuple:
    summary_rows = []
    taken_count = missed_count = unknown_count = 0

    for row in rows:
        item_name = extract_item_name(row, item_type)
        scheduled_time = extract_item_time(row, item_type)
        status_val, _snippet = infer_item_status_from_interactions(item_name, interactions, item_type)

        if status_val == "taken":
            taken_count += 1
        elif status_val == "missed":
            missed_count += 1
        else:
            unknown_count += 1

        summary_rows.append({
            "name": item_name,
            "time": scheduled_time,
            "status": status_val,
            "evidence": evidence_note(status_val, item_type),
        })

    return summary_rows, taken_count, missed_count, unknown_count


# ──────────────────────────────────────────────────────────────────────────────
# AI summary (returns structured dict instead of a plain string)
# ──────────────────────────────────────────────────────────────────────────────

def build_ai_summary(patient_name: str, interactions: list, days: int = REPORT_WINDOW_DAYS) -> dict:
    fallback = {
        "behavioral_summary": (
            f"Not enough conversation data was available to generate a behavioral summary "
            f"for the last {days} days."
        ),
        "recommended_caregiver_actions": [
            "Check in with the patient directly to learn more about their current wellbeing."
        ],
        "notable_patterns": [],
    }

    if not interactions:
        return fallback

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OPENAI_API_KEY in .env",
        )

    client = OpenAI()

    lines = []
    for row in interactions[:30]:
        ts = safe_text(pick_first(row, ("interaction_timestamp", "interaction_time", "created_at"), ""))
        user_said = safe_text(pick_first(row, ("user_text", "interaction_text", "message", "content"), ""))
        agent_said = safe_text(pick_first(row, ("assistant_text", "agent_text", "reply", "response"), ""))
        lines.append(f"[{ts}] Patient: {user_said} | Assistant: {agent_said}")

    system_prompt = (
        f"You are a compassionate clinical assistant generating a caregiver and doctor report "
        f"for an Alzheimer's patient.\n\n"
        f"Return ONLY valid JSON with exactly this structure:\n"
        f'{{\n'
        f'  "behavioral_summary": "One paragraph...",\n'
        f'  "recommended_caregiver_actions": ["Action 1", "Action 2"],\n'
        f'  "notable_patterns": ["Pattern 1"]\n'
        f'}}\n\n'
        f"Rules:\n"
        f"- behavioral_summary: warm, factual, useful for both caregiver and doctor. "
        f'Use phrases like "may suggest", "could indicate", "worth monitoring". '
        f"Never diagnose. If data is thin, say so gently.\n"
        f"- recommended_caregiver_actions: 3-5 specific, practical actions for a family caregiver. "
        f'Example: "Verify whether Panadol was taken." Not: "Monitor the patient."\n'
        f"- notable_patterns: 0-3 meaningful patterns for a clinician to review. Empty array if none.\n"
        f"- Do not mention AI systems, agents, technical errors, or system reliability.\n"
        f"- Unknown status means not confirmed, not necessarily missed.\n"
        f"- Return ONLY valid JSON. No preamble."
    )

    user_prompt = (
        f"Patient: {patient_name}\nReport period: last {days} days\n\nInteractions:\n"
        + "\n".join(lines)
    )

    try:
        response = client.responses.create(
            model=OPENAI_REPORT_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        result = json.loads(text)
        if not isinstance(result.get("behavioral_summary"), str):
            raise ValueError("missing behavioral_summary")
        if not isinstance(result.get("recommended_caregiver_actions"), list):
            raise ValueError("missing recommended_caregiver_actions")
        if not isinstance(result.get("notable_patterns"), list):
            result["notable_patterns"] = []
        return result
    except Exception:
        return fallback


# ──────────────────────────────────────────────────────────────────────────────
# PDF styles
# ──────────────────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "report_title": ps("ReportTitle", fontSize=22, leading=28,
            textColor=colors.HexColor("#1A3A6B"), fontName="Helvetica-Bold", spaceAfter=4),
        "report_subtitle": ps("ReportSubtitle", fontSize=10.5, leading=15,
            textColor=colors.HexColor("#4A6FA5"), fontName="Helvetica-Oblique", spaceAfter=4),
        "report_meta": ps("ReportMeta", fontSize=9, leading=13,
            textColor=colors.HexColor("#64748B"), spaceAfter=2),
        "section_heading": ps("SectionHeading", fontSize=13, leading=17,
            textColor=colors.HexColor("#1E3A8A"), fontName="Helvetica-Bold",
            spaceAfter=3, spaceBefore=6),
        "section_subtitle": ps("SectionSubtitle", fontSize=9, leading=13,
            textColor=colors.HexColor("#64748B"), fontName="Helvetica-Oblique", spaceAfter=5),
        "body": ps("Body", fontSize=10, leading=15,
            textColor=colors.HexColor("#334155"), spaceAfter=4),
        "label": ps("Label", fontSize=10, leading=14,
            textColor=colors.HexColor("#475569"), fontName="Helvetica-Bold"),
        "value": ps("Value", fontSize=10, leading=14,
            textColor=colors.HexColor("#1E293B")),
        "cell": ps("Cell", fontSize=9, leading=13,
            textColor=colors.HexColor("#334155")),
        "cell_small": ps("CellSmall", fontSize=8, leading=12,
            textColor=colors.HexColor("#64748B")),
        "glance_label": ps("GlanceLabel", fontSize=10, leading=15,
            textColor=colors.HexColor("#334155")),
        "action_item": ps("ActionItem", fontSize=10, leading=15,
            textColor=colors.HexColor("#1E293B"), spaceAfter=3, leftIndent=4),
        "chat_timestamp": ps("ChatTimestamp", fontSize=8, leading=12,
            textColor=colors.HexColor("#94A3B8"), fontName="Helvetica-Oblique"),
        "chat_label": ps("ChatLabel", fontSize=8.5, leading=13,
            textColor=colors.HexColor("#64748B"), fontName="Helvetica-Bold"),
        "chat_text": ps("ChatText", fontSize=9.5, leading=14,
            textColor=colors.HexColor("#1E293B"), spaceAfter=2),
        "empty_state": ps("EmptyState", fontSize=9.5, leading=14,
            textColor=colors.HexColor("#94A3B8"), fontName="Helvetica-Oblique", spaceAfter=6),
        "unknown_note": ps("UnknownNote", fontSize=8, leading=12,
            textColor=colors.HexColor("#78716C"), fontName="Helvetica-Oblique", spaceAfter=4),
        "adherence_line": ps("AdherenceLine", fontSize=10, leading=15,
            textColor=colors.HexColor("#334155"), spaceAfter=5),
        "repeat_text": ps("RepeatText", fontSize=9.5, leading=14,
            textColor=colors.HexColor("#78350F"), spaceAfter=6),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Page footer
# ──────────────────────────────────────────────────────────────────────────────

def _add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(
        A4[0] / 2,
        0.7 * cm,
        f"CogniCare  ·  Prepared for caregiver and clinical review  ·  Page {page_num}",
    )
    canvas.restoreState()


# ──────────────────────────────────────────────────────────────────────────────
# Section builders
# ──────────────────────────────────────────────────────────────────────────────

def _section_header(title: str, styles: dict, subtitle: str = None) -> list:
    elems = [Spacer(1, 0.45 * cm), Paragraph(title, styles["section_heading"])]
    if subtitle:
        elems.append(Paragraph(subtitle, styles["section_subtitle"]))
    return elems


def _build_header_section(patient_name: str, days: int, styles: dict) -> list:
    today = datetime.now()
    start = today - timedelta(days=days)
    date_range = (
        f"{start.strftime('%B')} {start.day} "
        f"– {today.strftime('%B')} {today.day}, {today.year}"
    )
    generated = f"{today.strftime('%B')} {today.day}, {today.year} at {_format_hm(today.hour, today.minute)}"

    data = [
        [Paragraph("CogniCare 5-Day Patient Report", styles["report_title"])],
        [Paragraph(
            "A gentle overview of care routines, reminders, and recent conversations.",
            styles["report_subtitle"],
        )],
        [Spacer(1, 0.15 * cm)],
        [Paragraph(f"<b>Patient:</b>  {_esc(patient_name)}", styles["report_meta"])],
        [Paragraph(f"<b>Report period:</b>  {date_range}", styles["report_meta"])],
        [Paragraph(f"<b>Generated:</b>  {generated}", styles["report_meta"])],
    ]
    t = Table(data, colWidths=[_PW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EBF4FB")),
        ("TOPPADDING", (0, 0), (0, 0), 20),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 2, colors.HexColor("#BFDBFE")),
    ]))
    return [t, Spacer(1, 0.4 * cm)]


def _build_patient_info_section(patient: dict, styles: dict) -> list:
    elems = _section_header("Patient Profile", styles)

    fields = [
        ("Full Name", f"{safe_text(patient.get('first_name'))} {safe_text(patient.get('last_name'))}".strip()),
        ("Date of Birth", format_date(patient.get("dob"))),
        ("Gender", safe_text(patient.get("gender"))),
        ("Diagnosis Stage", safe_text(patient.get("diagnosis_stage"))),
        ("Address", safe_text(patient.get("address"))),
        ("Contact Number", safe_text(patient.get("contact_no"))),
        ("Emergency Contact", safe_text(patient.get("emergency_contact"))),
    ]
    fields = [(k, v) for k, v in fields if v and v != "-"]

    data = [
        [Paragraph(f"<b>{_esc(k)}</b>", styles["label"]), Paragraph(_esc(v), styles["value"])]
        for k, v in fields
    ]
    t = Table(data, colWidths=[4.5 * cm, _PW - 4.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(t)
    return elems


def _build_care_at_a_glance_section(
    interactions: list,
    repeated_questions: list,
    meals_taken: int,
    meals_missed: int,
    meals_unknown: int,
    medications_taken: int,
    medications_missed: int,
    medications_unknown: int,
    activities_done: int,
    activities_missed: int,
    activities_unknown: int,
    styles: dict,
) -> list:
    elems = _section_header(
        "Care at a Glance",
        styles,
        subtitle="A quick snapshot before reading the full details below.",
    )

    def _badge(taken, missed, unknown, label):
        parts = []
        if taken:
            parts.append(f'<font color="#15803D"><b>{taken} confirmed</b></font>')
        if missed:
            parts.append(f'<font color="#DC2626"><b>{missed} missed</b></font>')
        if unknown:
            parts.append(f'<font color="#B45309">{unknown} unknown</font>')
        if not parts:
            parts = ['<font color="#94A3B8">No records found</font>']
        return f"<b>{label}:</b>  " + "  ·  ".join(parts)

    lines = [
        _badge(meals_taken, meals_missed, meals_unknown, "Meals"),
        _badge(medications_taken, medications_missed, medications_unknown, "Medications"),
        _badge(activities_done, activities_missed, activities_unknown, "Activities"),
        f"<b>Conversations reviewed:</b>  {len(interactions)}",
    ]
    if repeated_questions:
        top = repeated_questions[0]
        lines.append(
            f'<b>Repeated question noticed:</b>  '
            f'<i>&#8220;{_esc(top["text"][:70])}&#8221;</i>'
        )

    data = [[Paragraph(line, styles["glance_label"])] for line in lines]
    t = Table(data, colWidths=[_PW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFF")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DBEAFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#DBEAFE")),
    ]))
    elems.append(t)
    return elems


def _build_behavioral_overview_section(ai_summary: dict, styles: dict) -> list:
    elems = _section_header(
        "Behavioral Overview",
        styles,
        subtitle="Based on recorded conversations — describes recent engagement, mood signals, and care patterns.",
    )
    text = _esc(ai_summary.get("behavioral_summary", "No behavioral overview available."))
    card_data = [[Paragraph(text, styles["body"])]]
    t = Table(card_data, colWidths=[_PW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFF")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DBEAFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ]))
    elems.append(t)
    return elems



def _build_care_adherence_section(
    meal_summary: list,
    medication_summary: list,
    activity_summary: list,
    meals_taken: int,
    meals_missed: int,
    meals_unknown: int,
    medications_taken: int,
    medications_missed: int,
    medications_unknown: int,
    activities_done: int,
    activities_missed: int,
    activities_unknown: int,
    days: int,
    styles: dict,
) -> list:
    elems = _section_header(
        "Care Adherence Summary",
        styles,
        subtitle="How care routines were tracked and confirmed during this period.",
    )

    elems.append(Paragraph(
        f"<b>Meals:</b>  "
        f'<font color="#15803D">{meals_taken} confirmed</font>  ·  '
        f'<font color="#DC2626">{meals_missed} missed</font>  ·  '
        f'<font color="#B45309">{meals_unknown} unknown</font>',
        styles["adherence_line"],
    ))

    if medication_summary:
        for m in medication_summary:
            color = status_html_color(m["status"])
            label = status_display_label(m["status"], "medication")
            elems.append(Paragraph(
                f'<b>Medication · {_esc(m["name"])}:</b>  '
                f'<font color="{color}">{label}</font>',
                styles["adherence_line"],
            ))
    else:
        elems.append(Paragraph("<b>Medications:</b>  No records found.", styles["adherence_line"]))

    if activity_summary:
        for a in activity_summary:
            color = status_html_color(a["status"])
            label = status_display_label(a["status"], "activity")
            elems.append(Paragraph(
                f'<b>Activity · {_esc(a["name"])}:</b>  '
                f'<font color="{color}">{label}</font>',
                styles["adherence_line"],
            ))
    else:
        elems.append(Paragraph("<b>Activities:</b>  No records found.", styles["adherence_line"]))

    elems.append(Spacer(1, 0.2 * cm))
    elems.append(Paragraph(
        "<i>Unknown means the patient did not explicitly confirm completion during recorded "
        "conversations or reminders. It does not necessarily mean the task was missed.</i>",
        styles["unknown_note"],
    ))
    return elems


def _build_detail_table(summary_rows: list, item_type: str, styles: dict) -> "Table":
    label_col = {"meal": "Meal", "medication": "Medication", "activity": "Activity"}.get(item_type, "Item")
    header_bg = {"meal": "#E8F4EA", "medication": "#EAF0F8", "activity": "#F9EDEA"}.get(item_type, "#F1F5F9")
    col_widths = [4.5 * cm, 3.2 * cm, 3.0 * cm, _PW - 10.7 * cm]

    header = [
        Paragraph(f"<b>{label_col}</b>", styles["cell"]),
        Paragraph("<b>Scheduled Time</b>", styles["cell"]),
        Paragraph("<b>Status</b>", styles["cell"]),
        Paragraph("<b>Notes</b>", styles["cell"]),
    ]
    rows = [header]

    for row in summary_rows[:20]:
        st = row["status"]
        color = status_html_color(st)
        label = status_display_label(st, item_type)
        rows.append([
            Paragraph(_esc(row["name"]), styles["cell"]),
            Paragraph(format_time(row["time"]), styles["cell"]),
            Paragraph(f'<font color="{color}"><b>{label}</b></font>', styles["cell"]),
            Paragraph(_esc(row.get("evidence", "")), styles["cell_small"]),
        ])

    t = Table(rows, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFAFA")))
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_detail_section(
    summary_rows: list,
    item_type: str,
    days: int,
    styles: dict,
    title: str,
    subtitle: str = None,
) -> list:
    elems = _section_header(title, styles, subtitle=subtitle)
    if summary_rows:
        elems.append(_build_detail_table(summary_rows, item_type, styles))
        elems.append(Spacer(1, 0.1 * cm))
        elems.append(Paragraph(
            "<i>Unknown: No explicit confirmation was found in recorded conversations.</i>",
            styles["unknown_note"],
        ))
    else:
        elems.append(Paragraph(
            f"No {item_type} records were found for the last {days} days.",
            styles["empty_state"],
        ))
    return elems


def _build_conversation_highlights_section(interactions: list, styles: dict) -> list:
    elems = _section_header(
        "Conversation Highlights",
        styles,
        subtitle="Selected moments from recent patient interactions, reviewed for care-relevant content.",
    )

    if not interactions:
        elems.append(Paragraph(
            "No conversations were recorded during this period.", styles["empty_state"]
        ))
        return elems

    shown = 0
    for row in interactions[:15]:
        raw_ts = pick_first(row, ("interaction_timestamp", "interaction_time", "created_at", "timestamp"), "")
        user_text = str(pick_first(row, ("user_text", "interaction_text", "message", "content"), "") or "").strip()
        agent_raw = str(pick_first(row, ("assistant_text", "agent_text", "reply", "response"), "") or "").strip()
        agent_text = clean_conversation_text(agent_raw)

        if not user_text and not agent_raw:
            continue
        if not user_text and is_failed_assistant_response(agent_raw):
            continue

        ts_str = format_datetime(raw_ts) if raw_ts else "Time not recorded"

        patient_display = (
            f'&#8220;{_esc(user_text)}&#8221;' if user_text else "<i>(no patient message recorded)</i>"
        )
        agent_display = (
            f'&#8220;{_esc(agent_text)}&#8221;' if agent_text else "<i>(no response)</i>"
        )

        card_data = [
            [Paragraph(_esc(ts_str), styles["chat_timestamp"])],
            [Paragraph("<b>Patient</b>", styles["chat_label"])],
            [Paragraph(patient_display, styles["chat_text"])],
            [Paragraph("<b>Assistant</b>", styles["chat_label"])],
            [Paragraph(agent_display, styles["chat_text"])],
        ]
        card = Table(card_data, colWidths=[_PW])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DBEAFE")),
            ("TOPPADDING", (0, 0), (0, 0), 10),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        elems.append(card)
        elems.append(Spacer(1, 0.2 * cm))
        shown += 1

    if shown == 0:
        elems.append(Paragraph(
            "No conversation highlights were available for this period.", styles["empty_state"]
        ))

    return elems


def _build_repeated_questions_section(repeated_questions: list, styles: dict) -> list:
    if not repeated_questions:
        return []

    elems = _section_header(
        "Worth Noticing — Repeated Questions",
        styles,
        subtitle="These questions came up more than once and may suggest the patient is seeking reassurance.",
    )

    data = []
    for rq in repeated_questions[:5]:
        times_word = "times" if rq["count"] > 1 else "time"
        text = (
            f'The patient asked &#8220;{_esc(rq["text"][:120])}&#8221; '
            f'{rq["count"]} {times_word}. '
            f"A gentle reassurance or reminder may be helpful."
        )
        data.append([Paragraph(text, styles["repeat_text"])])

    t = Table(data, colWidths=[_PW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#FDE68A")),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#FDE68A")),
    ]))
    elems.append(t)
    return elems


# ──────────────────────────────────────────────────────────────────────────────
# Main PDF builder — public API (called by routers/reports.py)
# ──────────────────────────────────────────────────────────────────────────────

def build_patient_report_pdf(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> str:
    global _PW
    _ensure_reportlab_installed()
    _PW = A4[0] - 3.6 * cm  # 17.4 cm usable width with 1.8 cm margins each side

    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    interactions = get_interactions_for_patient(patient_id, days=days)
    medication_rows = try_get_patient_medications(patient_id, days=days)
    meal_rows = try_get_patient_meals(patient_id, days=days)
    activity_rows = try_get_patient_activities(patient_id, days=days)

    medication_summary, medications_taken, medications_missed, medications_unknown = build_item_summary(
        medication_rows, interactions, "medication"
    )
    meal_summary, meals_taken, meals_missed, meals_unknown = build_item_summary(
        meal_rows, interactions, "meal"
    )
    activity_summary, activities_done, activities_missed, activities_unknown = build_item_summary(
        activity_rows, interactions, "activity"
    )

    patient_name = f"{safe_text(patient.get('first_name'))} {safe_text(patient.get('last_name'))}".strip()
    ai_summary = build_ai_summary(patient_name, interactions, days=days)
    repeated_questions = group_repeated_questions(interactions)

    file_name = f"patient_report_{patient_id}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(REPORTS_DIR, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = _build_styles()
    story = []

    # 1 — Friendly report header
    story += _build_header_section(patient_name, days, styles)

    # 2 — Patient profile card
    story += _build_patient_info_section(patient, styles)

    # 3 — Care at a Glance
    story += _build_care_at_a_glance_section(
        interactions, repeated_questions,
        meals_taken, meals_missed, meals_unknown,
        medications_taken, medications_missed, medications_unknown,
        activities_done, activities_missed, activities_unknown,
        styles,
    )

    # 4 — Behavioral overview (AI paragraph)
    story += _build_behavioral_overview_section(ai_summary, styles)

    # 5 — Care adherence summary
    story += _build_care_adherence_section(
        meal_summary, medication_summary, activity_summary,
        meals_taken, meals_missed, meals_unknown,
        medications_taken, medications_missed, medications_unknown,
        activities_done, activities_missed, activities_unknown,
        days, styles,
    )

    story.append(PageBreak())

    # 7 — Meal details table
    story += _build_detail_section(
        meal_summary, "meal", days, styles,
        "Meal Details",
        subtitle="Meals scheduled during this period with confirmation status.",
    )

    story.append(Spacer(1, 0.4 * cm))

    # 8 — Medication details table
    story += _build_detail_section(
        medication_summary, "medication", days, styles,
        "Medication Details",
        subtitle="Medications scheduled during this period with confirmation status.",
    )

    story.append(Spacer(1, 0.4 * cm))

    # 9 — Activity details table
    story += _build_detail_section(
        activity_summary, "activity", days, styles,
        "Activity Details",
        subtitle="Activities scheduled during this period with confirmation status.",
    )

    story.append(PageBreak())

    # 10 — Conversation highlights (dialogue cards)
    story += _build_conversation_highlights_section(interactions, styles)

    # 11 — Repeated questions (only when patterns exist)
    if repeated_questions:
        story.append(Spacer(1, 0.3 * cm))
        story += _build_repeated_questions_section(repeated_questions, styles)

    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)
    return file_path


# ──────────────────────────────────────────────────────────────────────────────
# Metadata / file helpers — called by routers/reports.py
# ──────────────────────────────────────────────────────────────────────────────

def build_report_metadata(file_path: str) -> dict:
    return {"file_name": os.path.basename(file_path), "file_type": "application/pdf"}


def get_report_file_path(file_name: str) -> str:
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(REPORTS_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")
    return file_path
