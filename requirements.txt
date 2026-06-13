from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pyupbit
import asyncio
import time
import uvicorn
import os
import shutil
from database.session import engine, Base
from database.migrations import ensure_sqlite_schema
from auth.router import router as auth_router
from studio.router import router as studio_router
from trading.router import router as trading_router
from mobile.push import router as mobile_router
from billing.router import router as billing_router
from admin.router import router as admin_router
from support.router import router as support_router

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create DB tables
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

# Include Routers
app.include_router(auth_router)
app.include_router(studio_router)
app.include_router(trading_router)
app.include_router(mobile_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(support_router)

# Mount static folders
os.makedirs("uploads", exist_ok=True)
os.makedirs("static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend pages
@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/login.html", response_class=HTMLResponse)
async def serve_login():
    with open("static/login.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/finance.html", response_class=HTMLResponse)
async def serve_finance():
    with open("static/finance.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin.html", response_class=HTMLResponse)
async def serve_admin():
    with open("static/admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/studio.html", response_class=HTMLResponse)
async def serve_studio():
    with open("static/studio.html", "r", encoding="utf-8") as f:
        return f.read()



@app.get("/account.html", response_class=HTMLResponse)
async def serve_account():
    with open("static/account.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/customer.html", response_class=HTMLResponse)
async def serve_customer():
    with open("static/customer.html", "r", encoding="utf-8") as f:
        return f.read()

# FINANCE ENGINE is now modularized in trading/router.py


# STUDIO ENGINE is now modularized in studio/router.py

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)




