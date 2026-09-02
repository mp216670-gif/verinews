from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.article import Article, ArticleStatus
from app.models.verification import VerificationReport
from app.models.trust_score import TrustScore
from app.schemas.user import UserResponse, UserRoleUpdate
from app.api.deps import require_role

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """List all registered users (Admin only)."""
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Change the role of a user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent an admin from demoting themselves if they are the only admin
    if user.id == admin_user.id and payload.role != UserRole.ADMIN:
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the sole administrator")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.get("/metrics")
def get_system_metrics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
) -> Dict[str, Any]:
    """Retrieve platform verification statistics and trust score distributions (Admin only)."""
    total_users = db.query(User).count()
    users_by_role = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())

    total_articles = db.query(Article).count()
    articles_by_status = dict(db.query(Article.status, func.count(Article.id)).group_by(Article.status).all())

    total_verifications = db.query(VerificationReport).count()
    avg_score_res = db.query(func.avg(TrustScore.overall_score)).scalar()
    avg_score = round(float(avg_score_res), 1) if avg_score_res is not None else 0.0

    return {
        "users": {
            "total": total_users,
            "by_role": {str(k.value if hasattr(k, "value") else k): v for k, v in users_by_role.items()},
        },
        "articles": {
            "total": total_articles,
            "by_status": {str(k.value if hasattr(k, "value") else k): v for k, v in articles_by_status.items()},
        },
        "verifications": {
            "total_reports": total_verifications,
            "average_trust_score": avg_score,
        },
    }
