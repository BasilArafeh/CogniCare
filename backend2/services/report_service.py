import os
import uuid
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
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except Exception:  # pragma: no cover - handled by runtime check
    colors = None  # type: ignore[assignment]
    A4 = None  # type: ignore[assignment]
    ParagraphStyle = None  # type: ignore[assignment]
    getSampleStyleSheet = None  # type: ignore[assignment]
    cm = None  # type: ignore[assignment]
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


def _ensure_reportlab_installed() -> None:
    if SimpleDocTemplate is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ReportLab is not installed. Run: pip install reportlab",
        )


def safe_text(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def pick_first(row: dict, keys: tuple[str, ...], default=None):
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def parse_datetime_safe(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    value = str(value).strip()
    if not value:
        return None

    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def filter_rows_by_date_window(
    rows: list[dict],
    candidate_keys: tuple[str, ...],
    days: int,
    include_if_no_date: bool = False,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []

    for row in rows:
        raw_value = pick_first(row, candidate_keys, None)
        parsed = parse_datetime_safe(raw_value)

        if parsed is None:
            if include_if_no_date:
                filtered.append(row)
            continue

        if parsed >= cutoff:
            filtered.append(row)

    return filtered


def get_patient_by_id(patient_id: int) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("patients")
        .select("*")
        .eq("patient_id", patient_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_interactions_for_patient(patient_id: int, days: int = REPORT_WINDOW_DAYS, limit: int = 300) -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("interaction_log")
        .select("*")
        .eq("patient_id", patient_id)
        .limit(limit)
        .execute()
    )

    rows = result.data or []

    rows = filter_rows_by_date_window(
        rows,
        ("interaction_time", "created_at", "timestamp", "logged_at"),
        days=days,
        include_if_no_date=False,
    )

    def sort_key(row: dict):
        return pick_first(
            row,
            ("interaction_time", "created_at", "timestamp", "logged_at"),
            ""
        )

    rows.sort(key=sort_key, reverse=True)
    return rows


def try_get_patient_medications(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list[dict]:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_medications")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []

        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


def try_get_patient_meals(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list[dict]:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_meals")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []

        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


def try_get_patient_activities(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> list[dict]:
    client = get_supabase_client()
    try:
        result = (
            client.table("patient_activities")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )
        rows = result.data or []

        return filter_rows_by_date_window(
            rows,
            ("scheduled_datetime", "scheduled_at", "created_at", "date", "logged_at", "start_time"),
            days=days,
            include_if_no_date=True,
        )
    except Exception:
        return []


def extract_item_name(row: dict, item_type: str) -> str:
    if item_type == "meal":
        keys = ("meal_name", "food_name", "item_name", "name", "title")
    elif item_type == "medication":
        keys = ("medication_name", "medicine_name", "item_name", "name", "title")
    else:
        keys = ("activity_name", "item_name", "name", "title")

    return safe_text(pick_first(row, keys, "-"))


def extract_item_time(row: dict, item_type: str) -> str:
    if item_type == "meal":
        keys = ("meal_time", "scheduled_time", "time", "due_time")
    elif item_type == "medication":
        keys = ("scheduled_time", "time", "dose_time", "due_time")
    else:
        keys = ("start_time", "scheduled_time", "time", "due_time")

    return safe_text(pick_first(row, keys, "-"))


def extract_interaction_text(row: dict) -> str:
    return str(
        pick_first(
            row,
            ("interaction_text", "message", "content", "notes", "agent_text", "user_text"),
            ""
        )
    ).lower()


def infer_item_status_from_interactions(item_name: str, interactions: list[dict], item_type: str) -> str:
    """
    Returns:
    - taken
    - missed
    - unknown

    We ONLY infer from interaction_log because the schedule tables do not store completion status.
    """
    item_name_lower = item_name.strip().lower()

    if not item_name_lower or item_name_lower == "-":
        return "unknown"

    for row in interactions:
        text = extract_interaction_text(row)

        if item_name_lower not in text:
            continue

        if item_type == "meal":
            if any(phrase in text for phrase in [
                "did not eat", "didn't eat", "not eaten", "missed", "skipped", "skip"
            ]):
                return "missed"
            if any(phrase in text for phrase in [
                "ate", "eaten", "had", "finished", "completed"
            ]):
                return "taken"

        elif item_type == "medication":
            if any(phrase in text for phrase in [
                "did not take", "didn't take", "not taken", "missed", "skipped", "skip"
            ]):
                return "missed"
            if any(phrase in text for phrase in [
                "took", "taken", "completed", "done"
            ]):
                return "taken"

        elif item_type == "activity":
            if any(phrase in text for phrase in [
                "did not do", "didn't do", "not done", "missed", "skipped", "skip"
            ]):
                return "missed"
            if any(phrase in text for phrase in [
                "done", "completed", "finished", "performed"
            ]):
                return "taken"

    return "unknown"


def build_item_summary(rows: list[dict], interactions: list[dict], item_type: str) -> tuple[list[dict], int, int, int]:
    summary_rows = []
    taken_count = 0
    missed_count = 0
    unknown_count = 0

    for row in rows:
        item_name = extract_item_name(row, item_type)
        scheduled_time = extract_item_time(row, item_type)
        status_value = infer_item_status_from_interactions(item_name, interactions, item_type)

        if status_value == "taken":
            taken_count += 1
        elif status_value == "missed":
            missed_count += 1
        else:
            unknown_count += 1

        summary_rows.append(
            {
                "name": item_name,
                "time": scheduled_time,
                "status": status_value,
            }
        )

    return summary_rows, taken_count, missed_count, unknown_count


def summarize_interactions_with_openai(patient_name: str, interactions: list[dict], days: int = REPORT_WINDOW_DAYS) -> str:
    if not interactions:
        return f"No interaction summary is available for the last {days} days because no interactions were found."

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OPENAI_API_KEY in .env",
        )

    client = OpenAI()

    formatted_lines = []
    for row in interactions[:30]:
        timestamp = safe_text(
            pick_first(row, ("interaction_time", "created_at", "timestamp", "logged_at"))
        )
        interaction_type = safe_text(
            pick_first(row, ("interaction_type", "type", "category"))
        )
        text = safe_text(
            pick_first(
                row,
                ("interaction_text", "message", "content", "notes", "agent_text", "user_text"),
            )
        )
        formatted_lines.append(f"- Time: {timestamp} | Type: {interaction_type} | Text: {text}")

    interaction_text = "\n".join(formatted_lines)

    system_prompt = f"""
You are generating a caregiver-facing summary report for an Alzheimer’s care system.

Write a clear, professional, simple summary of the interactions between the patient and the AI agent during the last {days} days.
Focus on:
- the main themes discussed
- whether the patient sounded confused, repetitive, calm, distressed, or forgetful
- reminders or check-ins that happened
- medication-, meal-, or activity-related interactions if they appeared
- anything useful for a caregiver to understand the patient’s condition or behavior

Rules:
- Be factual and concise
- Do not invent details
- Do not use bullet points
- Write in plain, caregiver-friendly English
- Keep it around 1 short paragraph
""".strip()

    user_prompt = f"""
Patient name: {patient_name}

Here are recent interaction logs from the last {days} days:
{interaction_text}

Write the summary now.
""".strip()

    response = client.responses.create(
        model=OPENAI_REPORT_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.output_text.strip()


def build_patient_report_pdf(patient_id: int, days: int = REPORT_WINDOW_DAYS) -> str:
    _ensure_reportlab_installed()

    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

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
    interaction_summary = summarize_interactions_with_openai(patient_name, interactions, days=days)

    file_name = f"patient_report_{patient_id}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(REPORTS_DIR, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["BodyText"]

    summary_style = ParagraphStyle(
        "SummaryStyle",
        parent=normal_style,
        fontSize=10,
        leading=14,
        spaceAfter=10,
    )

    story = []

    story.append(Paragraph(f"CogniCare {days}-Day Caregiver Report", title_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.4 * cm))

    # Patient information
    story.append(Paragraph("Patient Information", heading_style))
    patient_table_data = [
        ["Patient ID", safe_text(patient.get("patient_id"))],
        ["Name", patient_name],
        ["Gender", safe_text(patient.get("gender"))],
        ["Date of Birth", safe_text(patient.get("dob"))],
        ["Diagnosis Stage", safe_text(patient.get("diagnosis_stage"))],
        ["Address", safe_text(patient.get("address"))],
        ["Contact Number", safe_text(patient.get("contact_no"))],
        ["Emergency Contact", safe_text(patient.get("emergency_contact"))],
    ]

    patient_table = Table(patient_table_data, colWidths=[5 * cm, 10 * cm])
    patient_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAEAEA")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(patient_table)
    story.append(Spacer(1, 0.4 * cm))

    # AI summary
    story.append(Paragraph("Interaction Summary", heading_style))
    story.append(Paragraph(interaction_summary, summary_style))
    story.append(Spacer(1, 0.2 * cm))

    # Summary metrics
    story.append(Paragraph("Care Summary Metrics", heading_style))
    stats_table_data = [
        ["Medications Confirmed Taken", safe_text(medications_taken)],
        ["Medications Confirmed Missed", safe_text(medications_missed)],
        ["Medications Unknown", safe_text(medications_unknown)],
        ["Meals Confirmed Taken", safe_text(meals_taken)],
        ["Meals Confirmed Missed", safe_text(meals_missed)],
        ["Meals Unknown", safe_text(meals_unknown)],
        ["Activities Confirmed Done", safe_text(activities_done)],
        ["Activities Confirmed Missed", safe_text(activities_missed)],
        ["Activities Unknown", safe_text(activities_unknown)],
        ["Total Interactions Logged", safe_text(len(interactions))],
    ]

    stats_table = Table(stats_table_data, colWidths=[8 * cm, 3 * cm])
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3EFE0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(stats_table)
    story.append(Spacer(1, 0.4 * cm))

    # Meal details
    story.append(Paragraph("Meal Details", heading_style))
    if meal_summary:
        meal_table_data = [["Meal", "Scheduled Time", "Status"]]
        for row in meal_summary[:15]:
            meal_table_data.append([row["name"], row["time"], row["status"]])

        meal_table = Table(meal_table_data, colWidths=[6 * cm, 4 * cm, 5 * cm])
        meal_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F4EA")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(meal_table)
    else:
        story.append(Paragraph(f"No meal records found for the last {days} days.", normal_style))

    story.append(Spacer(1, 0.3 * cm))

    # Medication details
    story.append(Paragraph("Medication Details", heading_style))
    if medication_summary:
        medication_table_data = [["Medication", "Scheduled Time", "Status"]]
        for row in medication_summary[:15]:
            medication_table_data.append([row["name"], row["time"], row["status"]])

        medication_table = Table(medication_table_data, colWidths=[6 * cm, 4 * cm, 5 * cm])
        medication_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F8")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(medication_table)
    else:
        story.append(Paragraph(f"No medication records found for the last {days} days.", normal_style))

    story.append(Spacer(1, 0.3 * cm))

    # Activity details
    story.append(Paragraph("Activity Details", heading_style))
    if activity_summary:
        activity_table_data = [["Activity", "Scheduled Time", "Status"]]
        for row in activity_summary[:15]:
            activity_table_data.append([row["name"], row["time"], row["status"]])

        activity_table = Table(activity_table_data, colWidths=[6 * cm, 4 * cm, 5 * cm])
        activity_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F9EDEA")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(activity_table)
    else:
        story.append(Paragraph(f"No activity records found for the last {days} days.", normal_style))

    story.append(Spacer(1, 0.4 * cm))

    # Recent interactions
    story.append(Paragraph("Recent Interaction Log Entries", heading_style))
    if interactions:
        interaction_rows = [["Time", "Type", "Text"]]
        for row in interactions[:10]:
            interaction_rows.append(
                [
                    safe_text(pick_first(row, ("interaction_time", "created_at", "timestamp", "logged_at"))),
                    safe_text(pick_first(row, ("interaction_type", "type", "category"))),
                    safe_text(pick_first(row, ("interaction_text", "message", "content", "notes", "agent_text", "user_text"))),
                ]
            )

        interaction_table = Table(interaction_rows, colWidths=[4 * cm, 3 * cm, 8 * cm])
        interaction_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7E7D9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(interaction_table)
    else:
        story.append(Paragraph(f"No recent interactions found for the last {days} days.", normal_style))

    doc.build(story)
    return file_path


def build_report_metadata(file_path: str) -> dict:
    file_name = os.path.basename(file_path)
    return {
        "file_name": file_name,
        "file_type": "application/pdf",
    }


def get_report_file_path(file_name: str) -> str:
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(REPORTS_DIR, safe_name)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    return file_path