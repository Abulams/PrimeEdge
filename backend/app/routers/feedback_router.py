import datetime
import io
import csv
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BetaFeedback, User
from ..auth import get_current_user_optional, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["Beta Feedback"])


class FeedbackSubmitRequest(BaseModel):
    category: str = "GENERAL"  # BUG, FEATURE, EXECUTION, UI_UX, GENERAL
    rating: Optional[int] = 5
    active_tab: Optional[str] = "find"
    selected_instrument: Optional[str] = "XAUUSD"
    message: str
    system_info: Optional[Dict[str, Any]] = None
    contact_email: Optional[str] = None


class FeedbackStatusUpdateRequest(BaseModel):
    status: str  # NEW, REVIEWED, RESOLVED
    admin_notes: Optional[str] = None


@router.post("/submit")
def submit_feedback(
    req: FeedbackSubmitRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Submits user feedback directly from the UI with auto-captured context.
    Works for both authenticated beta testers and anonymous submissions.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback message cannot be empty")

    user_id = current_user.id if current_user else None
    user_email = (current_user.email if current_user else req.contact_email) or "anonymous-tester@marketos.io"

    feedback_entry = BetaFeedback(
        user_id=user_id,
        user_email=user_email,
        category=req.category.upper(),
        rating=max(1, min(5, req.rating or 5)),
        active_tab=req.active_tab,
        selected_instrument=req.selected_instrument,
        message=req.message.strip(),
        system_info=req.system_info or {},
        status="NEW",
        created_at=datetime.datetime.utcnow()
    )

    db.add(feedback_entry)
    db.commit()
    db.refresh(feedback_entry)

    logger.info(f"📝 [Beta Feedback] New {feedback_entry.category} from {user_email} (ID #{feedback_entry.id})")
    return {
        "status": "SUCCESS",
        "feedback_id": feedback_entry.id,
        "message": "Thank you! Your feedback has been logged for quantitative review.",
        "created_at": feedback_entry.created_at.isoformat()
    }


@router.get("/list")
def list_feedback(
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lists beta feedback with statistical summaries for admin analysis."""
    query = db.query(BetaFeedback)

    if category and category != "ALL":
        query = query.filter(BetaFeedback.category == category.upper())
    if status_filter and status_filter != "ALL":
        query = query.filter(BetaFeedback.status == status_filter.upper())

    items = query.order_by(BetaFeedback.created_at.desc()).limit(limit).all()

    # Aggregate stats
    all_feedbacks = db.query(BetaFeedback).all()
    total_count = len(all_feedbacks)
    avg_rating = round(sum(f.rating or 5 for f in all_feedbacks) / max(1, total_count), 2) if total_count > 0 else 5.0
    
    category_counts = {}
    for f in all_feedbacks:
        category_counts[f.category] = category_counts.get(f.category, 0) + 1

    return {
        "summary": {
            "total_feedback": total_count,
            "average_rating": avg_rating,
            "category_breakdown": category_counts,
            "new_unreviewed": sum(1 for f in all_feedbacks if f.status == "NEW")
        },
        "items": [
            {
                "id": f.id,
                "user_email": f.user_email,
                "category": f.category,
                "rating": f.rating,
                "active_tab": f.active_tab,
                "selected_instrument": f.selected_instrument,
                "message": f.message,
                "system_info": f.system_info,
                "status": f.status,
                "admin_notes": f.admin_notes,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in items
        ]
    }


@router.patch("/{feedback_id}/status")
def update_feedback_status(
    feedback_id: int,
    req: FeedbackStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Admin updates the resolution status or notes for a feedback item."""
    feedback = db.query(BetaFeedback).filter(BetaFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    feedback.status = req.status.upper()
    if req.admin_notes is not None:
        feedback.admin_notes = req.admin_notes.strip()

    db.commit()
    db.refresh(feedback)
    return {"status": "UPDATED", "feedback_id": feedback.id, "current_status": feedback.status}


@router.get("/export-csv")
def export_feedback_csv(db: Session = Depends(get_db)):
    """Exports all beta feedback records to CSV for spreadsheet analytics."""
    items = db.query(BetaFeedback).order_by(BetaFeedback.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp (UTC)", "Tester Email", "Category", "Rating", "Active Screen", "Selected Asset", "Status", "Message", "Admin Notes"])

    for item in items:
        writer.writerow([
            item.id,
            item.created_at.isoformat() if item.created_at else "",
            item.user_email,
            item.category,
            item.rating,
            item.active_tab,
            item.selected_instrument,
            item.status,
            item.message,
            item.admin_notes or ""
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=market_os_beta_feedback_{datetime.date.today()}.csv"}
    )