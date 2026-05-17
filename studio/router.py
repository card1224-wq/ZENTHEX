import os
import shutil
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from auth.router import get_current_user
from database.session import get_db
try:
    import cv2
    import numpy as np
    from studio.cv_engine import process_image_to_3d
    STUDIO_WORKER_READY = True
except Exception as exc:
    cv2 = None
    np = None
    process_image_to_3d = None
    STUDIO_WORKER_READY = False
    STUDIO_WORKER_IMPORT_ERROR = str(exc)

router = APIRouter(prefix="/api/studio", tags=["studio"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024
TRIAL_USAGE_BY_IP: dict[str, str] = {}

def generate_3d_task(file_path: str, model_path: str, bg_path: str, style: str, wall_height: float):
    if not STUDIO_WORKER_READY:
        print(f"[Studio Worker] Worker unavailable: {STUDIO_WORKER_IMPORT_ERROR}")
        return
    try:
        process_image_to_3d(file_path, model_path, wall_height=wall_height, style=style, output_png_path=bg_path)
    except Exception as e:
        print(f"[Studio Worker] Task failed: {e}")

def get_optional_user(authorization: str | None, db: Session):
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

def charge_studio_trial_or_quota(user, db: Session, request: Request):
    if not user or not user_has_studio_access(user):
        today = time.strftime("%Y-%m-%d")
        client_ip = get_client_ip(request)
        if TRIAL_USAGE_BY_IP.get(client_ip) == today:
            raise HTTPException(
                status_code=403,
                detail="오늘의 무료 체험을 이미 사용했습니다. 내일 다시 체험하거나 Studio Pro 또는 Ultimate 구독 후 계속 사용할 수 있습니다.",
            )
        TRIAL_USAGE_BY_IP[client_ip] = today
        return

    if user.role == "owner":
        return
    if user.studio_generations_left <= 0:
        raise HTTPException(status_code=403, detail="무료 사용량을 모두 사용했습니다. Studio Pro 또는 Ultimate 구독이 필요합니다.")
    user.studio_generations_left -= 1
    db.commit()

def user_has_studio_access(user) -> bool:
    if not user:
        return False
    return user.role == "owner" or user.plan in ["studio_pro", "ultimate"]

def user_can_export(user) -> bool:
    return user_has_studio_access(user)

def prompt_to_floorplan(prompt: str):
    if not STUDIO_WORKER_READY:
        return None
    img = np.ones((1000, 1500), dtype=np.uint8) * 255
    lower = prompt.lower()
    margin = 90

    if "32평" in lower or "아파트" in lower:
        cv2.rectangle(img, (margin, margin), (1410, 910), (0, 0, 0), 10)
        cv2.line(img, (520, margin), (520, 910), (0, 0, 0), 7)
        cv2.line(img, (960, margin), (960, 620), (0, 0, 0), 7)
        cv2.line(img, (520, 430), (1410, 430), (0, 0, 0), 7)
        cv2.line(img, (960, 620), (1410, 620), (0, 0, 0), 7)
        cv2.putText(img, "Living", (150, 340), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3)
        cv2.putText(img, "Kitchen", (610, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3)
        cv2.putText(img, "Room", (1080, 280), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3)
        cv2.putText(img, "Bath", (1080, 550), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
        cv2.putText(img, "Room", (650, 700), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3)
    else:
        cv2.rectangle(img, (100, 100), (1400, 900), (0, 0, 0), 10)
        cv2.line(img, (520, 100), (520, 900), (0, 0, 0), 6)
        cv2.line(img, (950, 100), (950, 900), (0, 0, 0), 6)
        cv2.line(img, (100, 470), (1400, 470), (0, 0, 0), 6)
    return img

def describe_prompt_preview(prompt: str, source: str = "prompt"):
    lower = prompt.lower()
    if "32평" in lower or "아파트" in lower:
        return {
            "kind": "apartment_32",
            "title": "대한민국 32평 아파트",
            "summary": "거실, 주방, 침실 2개, 욕실, 현관 동선을 가진 아파트형 3D 미리보기입니다.",
            "rooms": ["거실", "주방", "침실 1", "침실 2", "욕실", "현관"],
        }
    if any(word in lower for word in ["카페", "루프탑", "통유리"]):
        return {
            "kind": "cafe",
            "title": "모던 루프탑 카페",
            "summary": "통유리 전면, 2층 매스, 루프탑 정원을 가진 상업 공간 미리보기입니다.",
            "rooms": ["라운지", "바", "계단", "루프탑"],
        }
    if any(word in lower for word in ["사무실", "오피스", "회의실"]):
        return {
            "kind": "office",
            "title": "업무 공간",
            "summary": "오픈 업무공간, 회의실, 라운지를 나눈 사무실형 3D 미리보기입니다.",
            "rooms": ["오픈 오피스", "회의실", "라운지", "포커스룸"],
        }
    if source == "upload":
        return {
            "kind": "uploaded_plan",
            "title": "업로드 도면 기반 공간",
            "summary": "업로드한 2D 도면을 기준으로 벽체와 공간 볼륨을 구성한 미리보기입니다.",
            "rooms": ["외벽", "내벽", "공간 볼륨"],
        }
    return {
        "kind": "premium",
        "title": "프리미엄 공간",
        "summary": "프롬프트를 기준으로 구성한 프리미엄 3D 공간 미리보기입니다.",
        "rooms": ["메인 공간", "보조 공간", "동선"],
    }

@router.post("/upload")
async def upload_floorplan(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    Authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    user = get_optional_user(Authorization, db)
    charge_studio_trial_or_quota(user, db, request)

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {file_ext}. JPG, PNG만 가능합니다.")

    safe_name = f"{int(time.time())}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다. 최대 10MB까지 가능합니다.")

    model_filename = f"{int(time.time())}.glb"
    model_path = f"static/models/{model_filename}"
    bg_filename = model_filename.replace(".glb", "_bg.png")
    bg_path = f"static/models/{bg_filename}"
    if STUDIO_WORKER_READY:
        background_tasks.add_task(generate_3d_task, file_path, model_path, bg_path, "premium", 25.0)

    can_export = user_can_export(user)
    return {
        "status": "success",
        "message": "3D 미리보기를 준비했습니다." if not STUDIO_WORKER_READY else "3D 생성 작업을 시작했습니다.",
        "preview": describe_prompt_preview(file.filename or "업로드 도면", "upload"),
        "preview_only": not can_export,
        "export_locked": not can_export,
        "model_url": f"/static/models/{model_filename}" if can_export and STUDIO_WORKER_READY else None,
        "bg_url": f"/static/models/{bg_filename}" if can_export and STUDIO_WORKER_READY else None,
        "worker_ready": STUDIO_WORKER_READY,
    }

@router.post("/generate")
async def generate_floorplan(
    background_tasks: BackgroundTasks,
    request: Request,
    prompt: str = Form(...),
    Authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    user = get_optional_user(Authorization, db)
    charge_studio_trial_or_quota(user, db, request)

    style = "gallery" if any(word in prompt.lower() for word in ["갤러리", "통유리", "카페"]) else "premium"
    wall_height = 24.0 if "아파트" in prompt.lower() else 30.0
    img = prompt_to_floorplan(prompt)

    filename = f"gen_prompt_{int(time.time())}"
    img_path = f"uploads/{filename}.jpg"
    if img is not None:
        cv2.imwrite(img_path, img)

    model_path = f"static/models/{filename}.glb"
    bg_path = f"static/models/{filename}_bg.png"
    if STUDIO_WORKER_READY and img is not None:
        background_tasks.add_task(generate_3d_task, img_path, model_path, bg_path, style, wall_height)

    can_export = user_can_export(user)
    return {
        "status": "success",
        "message": "프롬프트 기반 3D 미리보기를 준비했습니다." if not STUDIO_WORKER_READY else "프롬프트 기반 3D 생성 작업을 시작했습니다.",
        "preview": describe_prompt_preview(prompt),
        "preview_only": not can_export,
        "export_locked": not can_export,
        "model_url": f"/static/models/{filename}.glb" if can_export and STUDIO_WORKER_READY else None,
        "bg_url": f"/static/models/{filename}_bg.png" if can_export and STUDIO_WORKER_READY else None,
        "worker_ready": STUDIO_WORKER_READY,
    }
