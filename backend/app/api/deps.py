from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from common.database import get_db
from common import models
from common.config import settings
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

async def get_internal_secret_optional(
    x_internal_secret: Optional[str] = Header(None)
) -> Optional[str]:
    return x_internal_secret

async def get_current_user(
    token: Optional[str] = Query(None),
    auth_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    actual_token = token or auth_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not actual_token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(actual_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_optional(
    token: Optional[str] = Query(None),
    auth_token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    actual_token = token or auth_token
    if not actual_token:
        return None
    try:
        payload = jwt.decode(actual_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
        
    user = db.query(models.User).filter(models.User.email == email).first()
    return user

# async def get_current_admin_user(
#     current_user: models.User = Depends(get_current_user)
# ) -> models.User:
#     """
#     관리자 권한이 있는 사용자만 허용
#     """
#     if not current_user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="관리자 권한이 필요합니다."
#         )
#     return current_user
