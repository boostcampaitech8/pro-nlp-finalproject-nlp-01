from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from common import models
from common import schemas

class CoverLetterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cover_letters(self, user_id: int, recruitment_id: int = None):
        stmt = select(models.CoverLetter).where(models.CoverLetter.user_id == user_id).options(
            selectinload(models.CoverLetter.recruitment)
        )
        if recruitment_id:
            stmt = stmt.where(models.CoverLetter.recruitment_id == recruitment_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_cover_letter(self, cl_id: int, user_id: int):
        stmt = (
            select(models.CoverLetter)
            .options(selectinload(models.CoverLetter.items))
            .where(models.CoverLetter.id == cl_id, models.CoverLetter.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_cover_letter(self, cl: schemas.CoverLetterCreate):
        try:
            db_cl = models.CoverLetter(**cl.model_dump())
            self.db.add(db_cl)
            await self.db.commit()
            
            # Explicitly load relationships to prevent MissingGreenlet error
            stmt = select(models.CoverLetter).where(models.CoverLetter.id == db_cl.id).options(
                selectinload(models.CoverLetter.items),
                selectinload(models.CoverLetter.recruitment)
            )
            result = await self.db.execute(stmt)
            db_cl = result.scalar_one()
            
            return db_cl
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_cover_letter(self, cl_id: int, user_id: int, data: dict):
        try:
            db_cl = await self.get_cover_letter(cl_id, user_id)
            if not db_cl:
                return None
            
            for key, value in data.items():
                setattr(db_cl, key, value)
                
            await self.db.commit()
            await self.db.refresh(db_cl)
            return db_cl
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_cover_letter(self, cl_id: int, user_id: int):
        try:
            db_cl = await self.get_cover_letter(cl_id, user_id)
            if not db_cl:
                return False
            
            await self.db.delete(db_cl)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e

