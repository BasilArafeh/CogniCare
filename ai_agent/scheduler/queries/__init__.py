"""
Scheduler-only database access via Supabase REST (thin query modules).
"""

from scheduler.queries.patient_activities import select_activity_schedule_rows
from scheduler.queries.patient_meals import select_meal_schedule_rows
from scheduler.queries.patient_medications import select_medication_schedule_rows

__all__ = [
    "select_activity_schedule_rows",
    "select_meal_schedule_rows",
    "select_medication_schedule_rows",
]
