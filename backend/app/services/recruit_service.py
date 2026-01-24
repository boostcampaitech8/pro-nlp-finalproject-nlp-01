from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas

def get_recruitments(db: Session, skip: int = 0, limit: int = 10, category: str = None, keyword: str = None, location: str = None):
    query = db.query(models.Recruitment)
    if category and category != 'all':
        query = query.filter(models.Recruitment.category == category)
    if keyword:
        query = query.filter(models.Recruitment.title.contains(keyword) | models.Recruitment.company.contains(keyword))
    if location:
        query = query.filter(models.Recruitment.location.contains(location))
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total

def get_recruitment(db: Session, recruit_id: int):
    return db.query(models.Recruitment).filter(models.Recruitment.id == recruit_id).first()

def create_recruitment(db: Session, recruit: schemas.RecruitmentCreate):
    db_recruit = models.Recruitment(**recruit.model_dump())
    db.add(db_recruit)
    db.commit()
    db.refresh(db_recruit)
    return db_recruit

def update_recruitment(db: Session, recruit_id: int, recruit: schemas.RecruitmentCreate):
    db_recruit = get_recruitment(db, recruit_id)
    if not db_recruit:
        return None
    for key, value in recruit.model_dump().items():
        setattr(db_recruit, key, value)
    db.commit()
    db.refresh(db_recruit)
    return db_recruit

def delete_recruitment(db: Session, recruit_id: int):
    db_recruit = get_recruitment(db, recruit_id)
    if not db_recruit:
        return False
    db.delete(db_recruit)
    db.commit()
    return True
