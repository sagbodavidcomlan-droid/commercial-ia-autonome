from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas import ProjectCreate, Project as ProjectSchema, ProjectList
from app.models.user import User
from app.models.project import Project
from app.services.marketing_agent import MarketingAgentService

router = APIRouter()


@router.post("", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project and generate marketing content"""
    # Initialize marketing agent
    agent = MarketingAgentService(api_key=settings.ANTHROPIC_API_KEY)

    # Generate marketing content
    try:
        content = agent.generate_marketing_content(
            product_name=project_data.product_name,
            product_description=project_data.product_description,
            target_audience=project_data.target_audience,
            unique_selling_points=project_data.unique_selling_points
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate marketing content: {str(e)}"
        )

    # Create project in database
    new_project = Project(
        user_id=current_user.id,
        product_name=project_data.product_name,
        product_description=project_data.product_description,
        target_audience=project_data.target_audience,
        unique_selling_points=project_data.unique_selling_points,
        content=content
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project


@router.get("", response_model=List[ProjectList])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects for the current user"""
    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).order_by(Project.created_at.desc()).all()

    return projects


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project by ID"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    db.delete(project)
    db.commit()

    return None
