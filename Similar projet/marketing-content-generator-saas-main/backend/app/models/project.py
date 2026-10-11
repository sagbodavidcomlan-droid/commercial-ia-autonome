from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_name = Column(String, nullable=False)
    product_description = Column(Text, nullable=False)
    target_audience = Column(Text, nullable=False)
    unique_selling_points = Column(JSON, nullable=False)  # List of strings
    content = Column(JSON)  # Generated marketing content
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    owner = relationship("User", back_populates="projects")
