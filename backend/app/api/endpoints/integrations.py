from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import httpx
from typing import List

from common.database import get_async_db
from common import models, schemas
from common.config import settings
from app.api import deps

router = APIRouter()

@router.get("", response_model=List[schemas.UserIntegration])
async def list_integrations(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    stmt = select(models.UserIntegration).where(models.UserIntegration.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/github/auth-url")
async def get_github_auth_url(current_user: models.User = Depends(deps.get_current_user)):
    """Returns GitHub OAuth URL for frontend to redirect."""
    scope = "repo,read:user"
    url = f"https://github.com/login/oauth/authorize?client_id={settings.GH_OAUTH_CLIENT_ID}&redirect_uri={settings.GH_OAUTH_REDIRECT_URI}/api/integrations/github/callback&scope={scope}&state={current_user.id}"
    return {"url": url}

@router.get("/github/login")
async def github_login(
    user_id: int = None,
    current_user: models.User = Depends(deps.get_current_user_optional)
):
    """Redirects to GitHub for OAuth. Supports both authenticated and query param modes."""
    # Use user_id from query param if provided, otherwise from current_user
    uid = user_id if user_id else (current_user.id if current_user else None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    scope = "repo,read:user"
    url = f"https://github.com/login/oauth/authorize?client_id={settings.GH_OAUTH_CLIENT_ID}&redirect_uri={settings.GH_OAUTH_REDIRECT_URI}/api/integrations/github/callback&scope={scope}&state={uid}"
    return RedirectResponse(url)

@router.get("/github/callback")
async def github_callback(
    code: str, 
    state: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Handles GitHub OAuth callback."""
    # State is user_id
    user_id = int(state)
    
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for token
        res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GH_OAUTH_CLIENT_ID,
                "client_secret": settings.GH_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.GH_OAUTH_REDIRECT_URI}/api/integrations/github/callback"
            },
            headers={"Accept": "application/json"}
        )
        res_data = res.json()
        access_token = res_data.get("access_token")
        
        if not access_token:
             raise HTTPException(status_code=400, detail=f"Failed to get GitHub token: {res_data}")
        
        # 2. Get GitHub User ID (optional but good for uniqueness)
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )
        github_user = user_res.json()
        github_id = str(github_user.get("id"))
        
        # 3. Save or Update Integration
        stmt = select(models.UserIntegration).where(
            models.UserIntegration.user_id == user_id,
            models.UserIntegration.provider == "github"
        )
        result = await db.execute(stmt)
        integration = result.scalar_one_or_none()
        
        if integration:
            integration.access_token = access_token
            integration.provider_user_id = github_id
        else:
            integration = models.UserIntegration(
                user_id=user_id,
                provider="github",
                access_token=access_token,
                provider_user_id=github_id
            )
            db.add(integration)
            
        await db.commit()
        
    # Redirect back to frontend
    if settings.FRONTEND_URL:
        frontend_base = settings.FRONTEND_URL.rstrip('/')
    else:
        frontend_base = settings.BACKEND_URL.replace('api.', '').replace(':8000', ':3000').rstrip('/')
    
    frontend_url = f"{frontend_base}/my/portfolios/new?connected=github"
    return RedirectResponse(frontend_url)

@router.get("/github/repos")
async def list_github_repos(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lists repositories (public & private) for the connected GitHub account."""
    stmt = select(models.UserIntegration).where(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "github"
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=400, detail="GitHub not connected")
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"token {integration.access_token}"},
            params={"sort": "pushed", "per_page": 100}
        )
        if res.status_code != 200:
             raise HTTPException(status_code=res.status_code, detail="Failed to fetch repos from GitHub")
        
        repos = res.json()
        # Simplify data for frontend
        return [{
            "name": r["full_name"],
            "url": r["html_url"],
            "private": r["private"],
            "description": r["description"]
        } for r in repos]

@router.get("/notion/auth-url")
async def get_notion_auth_url(current_user: models.User = Depends(deps.get_current_user)):
    """Returns Notion OAuth URL for frontend to redirect."""
    if not settings.NOTION_OAUTH_CLIENT_ID or settings.NOTION_OAUTH_CLIENT_ID == "0":
        raise HTTPException(status_code=500, detail="Notion OAuth Client ID is not configured (received '0' or empty)")
        
    url = f"https://api.notion.com/v1/oauth/authorize?client_id={settings.NOTION_OAUTH_CLIENT_ID}&response_type=code&owner=user&redirect_uri={settings.NOTION_OAUTH_REDIRECT_URI}/api/integrations/notion/callback&state=user_{current_user.id}"
    return {"url": url}

@router.get("/notion/login")
async def notion_login(
    user_id: int = None,
    current_user: models.User = Depends(deps.get_current_user_optional)
):
    """Redirects to Notion for OAuth."""
    uid = user_id if user_id else (current_user.id if current_user else None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    if not settings.NOTION_OAUTH_CLIENT_ID or settings.NOTION_OAUTH_CLIENT_ID == "0":
        raise HTTPException(status_code=500, detail="Notion OAuth Client ID is not configured")
    
    url = f"https://api.notion.com/v1/oauth/authorize?client_id={settings.NOTION_OAUTH_CLIENT_ID}&response_type=code&owner=user&redirect_uri={settings.NOTION_OAUTH_REDIRECT_URI}/api/integrations/notion/callback&state=user_{uid}"
    return RedirectResponse(url)

@router.get("/notion/callback")
async def notion_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Handles Notion OAuth callback."""
    # State should be user_{id}
    try:
        user_id = int(state.replace("user_", ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for token
        import base64
        auth_string = f"{settings.NOTION_OAUTH_CLIENT_ID}:{settings.NOTION_OAUTH_CLIENT_SECRET}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        res = await client.post(
            "https://api.notion.com/v1/oauth/token",
            headers={
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.NOTION_OAUTH_REDIRECT_URI}/api/integrations/notion/callback"
            }
        )
        
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get Notion token: {res.text}")
        
        res_data = res.json()
        access_token = res_data.get("access_token")
        workspace_id = res_data.get("workspace_id")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # 2. Save or Update Integration
        stmt = select(models.UserIntegration).where(
            models.UserIntegration.user_id == user_id,
            models.UserIntegration.provider == "notion"
        )
        result = await db.execute(stmt)
        integration = result.scalar_one_or_none()
        
        if integration:
            integration.access_token = access_token
            integration.provider_user_id = workspace_id
        else:
            integration = models.UserIntegration(
                user_id=user_id,
                provider="notion",
                access_token=access_token,
                provider_user_id=workspace_id
            )
            db.add(integration)
        
        await db.commit()
    
    # Redirect back to frontend
    if settings.FRONTEND_URL:
        frontend_base = settings.FRONTEND_URL.rstrip('/')
    else:
        frontend_base = settings.BACKEND_URL.replace('api.', '').replace(':8000', ':3000').rstrip('/')
        
    frontend_url = f"{frontend_base}/my/portfolios/new?connected=notion"
    return RedirectResponse(frontend_url)

@router.get("/notion/pages")
async def list_notion_pages(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lists accessible pages from the connected Notion workspace."""
    stmt = select(models.UserIntegration).where(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "notion"
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=400, detail="Notion not connected")
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.notion.com/v1/search",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                "filter": {"property": "object", "value": "page"},
                "page_size": 100
            }
        )
        
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Failed to fetch pages from Notion")
        
        pages = res.json().get("results", [])
        # Simplify data for frontend and filter for top-level pages only
        return [{
            "id": p["id"],
            "title": p.get("properties", {}).get("title", {}).get("title", [{}])[0].get("plain_text", "Untitled") 
                     if "title" in p.get("properties", {}) 
                     else p.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled"),
            "url": p["url"]
        } for p in pages if p.get("parent", {}).get("type") == "workspace"]

@router.delete("/{integration_id}")
async def remove_integration(
    integration_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    stmt = delete(models.UserIntegration).where(
        models.UserIntegration.id == integration_id,
        models.UserIntegration.user_id == current_user.id
    )
    await db.execute(stmt)
    await db.commit()
    return {"success": True}

@router.get("/blog/posts")
async def list_blog_posts(url: str):
    """
    Fetches a list of blog posts from a profile URL (Velog/Tistory).
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # We use a simple scraping logic here to avoid dependency issues with 'jobs' package
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            posts = []

            if "velog.io" in url:
                articles = soup.find_all("div", {"class": "sc-hHTYSt"}) or soup.find_all("article")
                for article in articles:
                    link_tag = article.find("a")
                    title_tag = article.find("h2")
                    if link_tag and title_tag and link_tag.get("href"):
                        href = link_tag.get("href")
                        full_url = href if href.startswith("http") else f"https://velog.io{href}"
                        posts.append({
                            "title": title_tag.get_text(strip=True),
                            "url": full_url
                        })
            elif "tistory.com" in url:
                links = soup.select("a[href*='/']")
                for link in links:
                    href = link.get("href", "")
                    if any(x in href for x in ["/category", "?page="]) or len(href.split("/")) < 2:
                        continue
                    title = link.get_text(strip=True)
                    if title and len(title) > 2:
                        full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                        posts.append({"title": title, "url": full_url})
            
            seen = set()
            unique_posts = []
            for p in posts:
                if p["url"] not in seen:
                    unique_posts.append(p)
                    seen.add(p["url"])
            return unique_posts[:20]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Blog discovery failed: {e}")
        return []

