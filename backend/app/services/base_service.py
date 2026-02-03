from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import TypeVar, Type, List, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseService:
    """
    Base service class providing common database operations.
    All service classes should inherit from this to ensure consistent patterns.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_with_relationships(
        self, 
        model: Type[T], 
        id: int, 
        relationships: List[str],
        raise_if_not_found: bool = False
    ) -> Optional[T]:
        """
        Get a model instance with explicitly loaded relationships.
        Prevents MissingGreenlet errors by using selectinload.
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            relationships: List of relationship attribute names to load
            raise_if_not_found: If True, raises exception when not found
            
        Returns:
            Model instance or None if not found
            
        Example:
            portfolio = await self.get_with_relationships(
                Portfolio, 
                portfolio_id, 
                ['job_queries', 'owner']
            )
        """
        options = [selectinload(getattr(model, rel)) for rel in relationships]
        stmt = select(model).where(model.id == id).options(*options)
        result = await self.db.execute(stmt)
        instance = result.scalar_one_or_none()
        
        if not instance and raise_if_not_found:
            from common.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(model.__name__, id)
        
        return instance
    
    async def create_with_relationships(
        self,
        instance: T,
        relationships: List[str]
    ) -> T:
        """
        Create a model instance and explicitly load its relationships.
        Prevents MissingGreenlet errors when returning the created instance.
        
        Args:
            instance: SQLAlchemy model instance to create
            relationships: List of relationship attribute names to load
            
        Returns:
            Created model instance with relationships loaded
            
        Example:
            portfolio = Portfolio(project_name="My Project", ...)
            created = await self.create_with_relationships(
                portfolio, 
                ['job_queries']
            )
        """
        try:
            self.db.add(instance)
            await self.db.commit()
            
            # Reload with relationships
            model_class = type(instance)
            return await self.get_with_relationships(
                model_class,
                instance.id,
                relationships,
                raise_if_not_found=True
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create {type(instance).__name__}: {e}")
            raise
    
    async def safe_commit(self):
        """
        Safely commit transaction with automatic rollback on error.
        """
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction commit failed: {e}")
            raise
    
    async def safe_delete(self, instance: T) -> bool:
        """
        Safely delete an instance with automatic rollback on error.
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            await self.db.delete(instance)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete {type(instance).__name__}: {e}")
            return False
