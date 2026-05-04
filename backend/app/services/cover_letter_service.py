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
        db_cl = result.scalar_one_or_none()
        
        if db_cl and db_cl.items:
            # Sort items by order_index in memory if relationship wasn't ordered by default
            db_cl.items.sort(key=lambda x: x.order_index if x.order_index is not None else 0)
            
        return db_cl

    async def create_cover_letter(self, cl: schemas.CoverLetterCreate):
        try:
            cl_dict = cl.model_dump()
            questions_data = cl_dict.pop('questions', [])
            
            db_cl = models.CoverLetter(**cl_dict)
            self.db.add(db_cl)
            await self.db.flush()
            
            for i, q_data in enumerate(questions_data):
                db_item = models.CoverLetterItem(
                    **q_data, 
                    cover_letter_id=db_cl.id,
                    order_index=i
                )
                self.db.add(db_item)
                
            await self.db.commit()
            
            # Explicitly load relationships to prevent MissingGreenlet error
            stmt = select(models.CoverLetter).where(models.CoverLetter.id == db_cl.id).options(
                selectinload(models.CoverLetter.items),
                selectinload(models.CoverLetter.recruitment)
            )
            result = await self.db.execute(stmt)
            db_cl = result.scalar_one()
            
            if db_cl.items:
                db_cl.items.sort(key=lambda x: x.order_index if x.order_index is not None else 0)
                
            return db_cl
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_cover_letter(self, cl_id: int, user_id: int, data: dict):
        try:
            db_cl = await self.get_cover_letter(cl_id, user_id)
            if not db_cl:
                return None
            
            # --- Version History Snapshot ---
            # Save current state before update
            items_snapshot = [
                {"question": it.question, "content": it.content, "order_index": it.order_index}
                for it in sorted(db_cl.items, key=lambda x: x.order_index if x.order_index is not None else 0)
            ]
            version = models.CoverLetterVersion(
                cover_letter_id=cl_id,
                title=db_cl.title,
                items_snapshot=items_snapshot
            )
            self.db.add(version)
            
            # --- Perform Update ---
            questions_data = data.pop('questions', None)
            
            for key, value in data.items():
                setattr(db_cl, key, value)
            
            if questions_data is not None:
                # Simple replacement logic for questions
                # 1. Delete existing items
                from sqlalchemy import delete
                await self.db.execute(
                    delete(models.CoverLetterItem).where(models.CoverLetterItem.cover_letter_id == cl_id)
                )
                
                # 2. Add new items with preservation of order
                for i, q_data in enumerate(questions_data):
                    db_item = models.CoverLetterItem(
                        **q_data, 
                        cover_letter_id=cl_id,
                        order_index=i
                    )
                    self.db.add(db_item)
                
            await self.db.commit()
            await self.db.refresh(db_cl)
            
            # Re-sort for consistent return
            if db_cl.items:
                db_cl.items.sort(key=lambda x: x.order_index if x.order_index is not None else 0)
                
            return db_cl
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_cover_letter_versions(self, cl_id: int, user_id: int):
        # Verify ownership
        db_cl = await self.get_cover_letter(cl_id, user_id)
        if not db_cl:
            return []
            
        stmt = (
            select(models.CoverLetterVersion)
            .where(models.CoverLetterVersion.cover_letter_id == cl_id)
            .order_by(models.CoverLetterVersion.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

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

    async def confirm_cover_letter(self, cl_id: int, user_id: int):
        # Already handled in endpoint, but good to have here
        try:
            db_cl = await self.get_cover_letter(cl_id, user_id)
            if not db_cl:
                return None
            db_cl.processing_status = models.ProcessingStatus.COMPLETED
            await self.db.commit()
            await self.db.refresh(db_cl)
            return db_cl
        except Exception as e:
            await self.db.rollback()
            raise e

