import os
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.database import get_async_db
from common import models
from jose import jwt
from datetime import datetime, timedelta

from common.config import settings
from app.api import deps
from common import schemas

router = APIRouter()

# Environment variables are now in settings
# KAKAO_* and JWT settings are accessed via settings.X

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.get("/kakao/callback")
async def kakao_callback(
    code: str, 
    redirect_uri: Optional[str] = None, 
    db: AsyncSession = Depends(get_async_db)
):
    # If frontend provides redirect_uri, use it exactly as is.
    # Otherwise, use the one from settings and append the callback path.
    if redirect_uri:
        actual_redirect_uri = redirect_uri
    else:
        actual_redirect_uri = f"{settings.KAKAO_REDIRECT_URI}/api/auth/kakao/callback"
    
    # 1. Exchange code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "redirect_uri": actual_redirect_uri,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get token: {token_res.text}")
        
        token_data = token_res.json()
        access_token = token_data.get("access_token")

        # 2. Get user info
        user_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        kakao_user = user_res.json()
        kakao_account = kakao_user.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        
        email = kakao_account.get("email")
        if not email:
            # Fallback for kakao account without email (using internal ID)
            email = f"{kakao_user['id']}@kakao.com"
            
        name = profile.get("nickname", "Kakao User")
        profile_image = profile.get("profile_image_url")

        # 3. DB Check & Create
        stmt = select(models.User).where(models.User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = models.User(
                email=email,
                name=name
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # 4. Create Local Token
        local_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        
        return {
            "access_token": local_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "profile_summary": user.profile_summary,
                "desired_job_title": user.desired_job_title
            }
        }

@router.get("/me", response_model=schemas.User)
async def get_me(current_user: models.User = Depends(deps.get_current_user)):
    return current_user
