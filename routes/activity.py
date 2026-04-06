"""Shared helper for writing to the activity log."""
from flask_login import current_user
from models import db, ActivityLog


def log_activity(vehicle_id: int, action: str, details: str = None):
    """Write one line to the activity log. Safe to call inside any request context."""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    entry = ActivityLog(
        vehicle_id=vehicle_id,
        user_id=user_id,
        action=action,
        details=details,
    )
    db.session.add(entry)
    # Caller is responsible for committing the surrounding transaction
