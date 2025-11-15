"""
Frontend Microservice - Web Interface for Recommendation Engine

Provides a user-friendly web interface to interact with the recommendation engine.
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import httpx
from typing import Optional

# Configuration
BACKEND_URL = "http://backend:8000/api/v1"

app = FastAPI(
    title="Recommendation Engine - Frontend",
    version="1.0.0",
    description="Web interface for the Recommendation Engine"
)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
static_path = Path("app/static")
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def list_users(request: Request):
    """List all users"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL}/users")
            users = response.json() if response.status_code == 200 else []
        except Exception as e:
            users = []
            error = str(e)

    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users}
    )


@app.get("/users/create", response_class=HTMLResponse)
async def create_user_form(request: Request):
    """Create user form"""
    return templates.TemplateResponse("create_user.html", {"request": request})


@app.post("/users/create")
async def create_user(
    username: str = Form(...),
    email: str = Form(...)
):
    """Create a new user"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/users",
                json={"username": username, "email": email, "preferences": {}}
            )

            if response.status_code == 201:
                return RedirectResponse(url="/users", status_code=303)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/items", response_class=HTMLResponse)
async def list_items(request: Request, category: Optional[str] = None):
    """List all items"""

    async with httpx.AsyncClient() as client:
        try:
            url = f"{BACKEND_URL}/items"
            if category:
                url += f"?category={category}"

            response = await client.get(url)
            items = response.json() if response.status_code == 200 else []
        except Exception as e:
            items = []

    return templates.TemplateResponse(
        "items.html",
        {"request": request, "items": items, "selected_category": category}
    )


@app.get("/items/create", response_class=HTMLResponse)
async def create_item_form(request: Request):
    """Create item form"""
    return templates.TemplateResponse("create_item.html", {"request": request})


@app.post("/items/create")
async def create_item(
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
    tags: str = Form("")
):
    """Create a new item"""

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/items",
                json={
                    "title": title,
                    "description": description,
                    "category": category,
                    "tags": tag_list,
                    "features": {}
                }
            )

            if response.status_code == 201:
                return RedirectResponse(url="/items", status_code=303)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{user_id}", response_class=HTMLResponse)
async def get_recommendations(
    request: Request,
    user_id: int,
    algorithm: str = "hybrid",
    top_n: int = 10
):
    """Get recommendations for a user"""

    async with httpx.AsyncClient() as client:
        try:
            # Get user info
            user_response = await client.get(f"{BACKEND_URL}/users/{user_id}")
            user = user_response.json() if user_response.status_code == 200 else None

            # Get recommendations
            rec_response = await client.get(
                f"{BACKEND_URL}/recommendations/user/{user_id}",
                params={"algorithm": algorithm, "top_n": top_n}
            )

            recommendations = rec_response.json() if rec_response.status_code == 200 else None

        except Exception as e:
            user = None
            recommendations = None
            error = str(e)

    return templates.TemplateResponse(
        "recommendations.html",
        {
            "request": request,
            "user": user,
            "recommendations": recommendations,
            "algorithm": algorithm
        }
    )


@app.get("/interact", response_class=HTMLResponse)
async def interact_form(request: Request):
    """Interaction form"""

    async with httpx.AsyncClient() as client:
        try:
            users_response = await client.get(f"{BACKEND_URL}/users")
            users = users_response.json() if users_response.status_code == 200 else []

            items_response = await client.get(f"{BACKEND_URL}/items")
            items = items_response.json() if items_response.status_code == 200 else []

        except Exception:
            users = []
            items = []

    return templates.TemplateResponse(
        "interact.html",
        {"request": request, "users": users, "items": items}
    )


@app.post("/interact")
async def create_interaction(
    user_id: int = Form(...),
    item_id: int = Form(...),
    interaction_type: str = Form(...),
    rating: Optional[float] = Form(None)
):
    """Create a new interaction"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/interactions",
                json={
                    "user_id": user_id,
                    "item_id": item_id,
                    "interaction_type": interaction_type,
                    "rating": rating,
                    "weight": 1.0
                }
            )

            if response.status_code == 201:
                return RedirectResponse(
                    url=f"/recommendations/{user_id}",
                    status_code=303
                )
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/ab-tests", response_class=HTMLResponse)
async def list_ab_tests(request: Request):
    """List all A/B tests"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL}/ab-tests")
            ab_tests = response.json() if response.status_code == 200 else []
        except Exception:
            ab_tests = []

    return templates.TemplateResponse(
        "ab_tests.html",
        {"request": request, "ab_tests": ab_tests}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL.replace('/api/v1', '')}/health")
            backend_status = response.json() if response.status_code == 200 else {"status": "unhealthy"}
        except Exception:
            backend_status = {"status": "unreachable"}

    return {
        "status": "healthy",
        "backend": backend_status
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
