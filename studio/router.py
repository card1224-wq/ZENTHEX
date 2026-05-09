import uuid
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, Depends, Header, HTTPException
import time
import shutil
import os
from sqlalchemy.orm import Session
from database.session import get_db
from auth.router import get_current_user
from studio.cv_engine import process_image_to_3d
import cv2
import numpy as np

router = APIRouter(prefix="/api/studio", tags=["studio"])

# In a full production env, we'd use Celery instead of FastAPI BackgroundTasks
def generate_3d_task(file_path: str, model_path: str, bg_path: str, style: str, wall_height: float):
    try:
        process_image_to_3d(file_path, model_path, wall_height=wall_height, style=style, output_png_path=bg_path)
    except Exception as e:
        print(f"[Studio Worker] Task failed: {e}")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

@router.post("/upload")
async def upload_floorplan(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    Authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Authentication required for 3D Generation")
    
    # 1. 파일 확장자 검증
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}. Only JPG, PNG allowed.")
    
    # 2. 파일 크기 검증 (파일을 읽기 전에 확인)
    # Note: 일부 라이브러리 없이 정확한 크기 체크를 위해 임시 저장을 먼저 하되, 넘어서면 바로 삭제
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    if user.studio_generations_left <= 0:
        raise HTTPException(status_code=403, detail="Generation quota exceeded. Please upgrade your plan in Zenthex Billing.")
    
    # Deduct quota
    user.studio_generations_left -= 1
    db.commit()

    print(f"[Studio Engine - AI Prompter] Receiving floorplan: {file.filename}")
    safe_name = f"{int(time.time())}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    
    # 3. 실제 저장 및 크기 사후 검증
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File too large (Max 10MB)")
    
    model_filename = f"{int(time.time())}.glb"
    demo_model_path = f"static/models/{model_filename}"
    bg_filename = model_filename.replace('.glb', '_bg.png')
    bg_path = f"static/models/{bg_filename}"
    
    ai_style = "premium"
    ai_wall_height = 25.0
    
    # Run heavy 3D conversion in Background
    background_tasks.add_task(generate_3d_task, file_path, demo_model_path, bg_path, ai_style, ai_wall_height)
    
    return {
        "status": "success", 
        "message": "3D Generation Started in Background", 
        "model_url": f"/static/models/{model_filename}",
        "bg_url": f"/static/models/{bg_filename}"
    }

@router.post("/generate")
async def generate_floorplan(
    background_tasks: BackgroundTasks, 
    prompt: str = Form(...),
    Authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Authentication required for 3D Generation")
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    if user.studio_generations_left <= 0:
        raise HTTPException(status_code=403, detail="Generation quota exceeded. Please upgrade your plan in Zenthex Billing.")
    
    # Deduct quota
    user.studio_generations_left -= 1
    db.commit()
    
    print(f"[Studio Engine - AI Prompter] Generating AI parameters for: {prompt}")
    
    style = "premium"
    if "갤러리" in prompt.lower() or "통유리" in prompt.lower():
        style = "gallery"
        
    img = np.ones((1000, 1500), dtype=np.uint8) * 255
    cv2.rectangle(img, (100, 100), (1400, 900), (0,0,0), 10)
    
    filename = f"gen_prompt_{int(time.time())}"
    img_path = f"uploads/{filename}.jpg"
    cv2.imwrite(img_path, img)
    
    demo_model_path = f"static/models/{filename}.glb"
    bg_path = f"static/models/{filename}_bg.png"
    
    background_tasks.add_task(generate_3d_task, img_path, demo_model_path, bg_path, style, 30.0)
    
    return {
        "status": "success", 
        "message": "AI Text prompt interpreted and task started", 
        "model_url": f"/static/models/{filename}.glb"
    }
