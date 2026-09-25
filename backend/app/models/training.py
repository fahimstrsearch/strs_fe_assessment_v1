"""A graded trainee attempt.

Created when a trainee submits an underwriting. Links the attempt to the
reference underwriting it was scored against and keeps the score breakdown
so the dashboard can explain the rating.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrainingSubmission(Base):
    __tablename__ = "training_submissions"
    __table_args__ = (
        Index("ix_training_submissions_zpid", "zpid"),
        Index("ix_training_submissions_underwriting_id", "underwriting_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    underwriting_id = Column(
        Integer,
        ForeignKey("underwritings.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_underwriting_id = Column(
        Integer,
        ForeignKey("underwritings.id", ondelete="SET NULL"),
        nullable=True,
    )
    zpid = Column(
        Text,
        ForeignKey("properties.zpid", ondelete="CASCADE"),
        nullable=False,
    )

    # best | medium | low
    rating = Column(String(10), nullable=False)
    # 100 / 70 / 40, matching the rating.
    accuracy = Column(Numeric(5, 2), nullable=False)
    # {rating, accuracy, candidate, reference, deviation, thresholds}
    breakdown = Column(JSONB, nullable=False)
    submitted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    underwriting = relationship(
        "Underwriting", back_populates="submissions", foreign_keys=[underwriting_id]
    )
    reference_underwriting = relationship(
        "Underwriting", foreign_keys=[reference_underwriting_id]
    )
