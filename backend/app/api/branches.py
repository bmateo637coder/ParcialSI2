from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.branch import Branch
from app.schemas import BranchCreate, BranchResponse
from typing import List, Optional

router = APIRouter()

@router.get("/", response_model=List[BranchResponse])
def get_branches(city: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Branch).filter(Branch.is_active == True)
    if city:
        query = query.filter(Branch.city.ilike(f"%{city}%"))
    return query.all()

@router.post("/", response_model=BranchResponse)
def create_branch(branch: BranchCreate, db: Session = Depends(get_db)):
    new_branch = Branch(**branch.model_dump())
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch
