import os
import asyncio
from pathlib import Path
import shutil
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from auth.router import get_current_user
from database.session import get_db
from studio.providers.nanobanana import generate_preview_image, is_configured as google_ai_studio_is_configured
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

def charge_studio_trial_or_quota(user, db: Session, request: Request, *, commit=True):
    if not user or not user_has_studio_access(user):
        today = time.strftime("%Y-%m-%d")
        client_ip = get_client_ip(request)
        if TRIAL_USAGE_BY_IP.get(client_ip) == today:
            raise HTTPException(
                status_code=403,
                detail="오늘의 무료 체험을 이미 사용했습니다. 내일 다시 체험하거나 Studio Pro 또는 Ultimate 구독 후 계속 사용할 수 있습니다.",
            )
        if commit:
            TRIAL_USAGE_BY_IP[client_ip] = today
        return

    if user.role == "owner":
        return
    if user.studio_generations_left <= 0:
        raise HTTPException(status_code=403, detail="무료 사용량을 모두 사용했습니다. Studio Pro 또는 Ultimate 구독이 필요합니다.")
    if commit:
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

def build_google_ai_studio_result(prompt: str, reference_image_path: str | None = None):
    if not google_ai_studio_is_configured():
        return {"status": "skipped", "message": "GEMINI_API_KEY가 없어 Google AI Studio/Gemini 3D 이미지를 건너뛰고 Studio 기본 미리보기를 사용합니다."}
    return generate_preview_image(prompt, reference_image_path=reference_image_path)

# One expensive request per worker; do not block the trading event loop.
GENERATION_LOCK = asyncio.Lock()


async def create_image_result(prompt, user, db, request, reference=None):
    if not google_ai_studio_is_configured():
        raise HTTPException(503, "AI 이미지 생성 연결이 아직 설정되지 않았습니다. 샘플 보기는 생성 결과가 아닙니다.")
    if GENERATION_LOCK.locked():
        raise HTTPException(429, "다른 이미지 생성 작업을 처리 중입니다. 완료 후 다시 요청하세요.")
    async with GENERATION_LOCK:
        charge_studio_trial_or_quota(user, db, request, commit=False)
        result = await asyncio.to_thread(build_google_ai_studio_result, prompt, reference)
        image_url = result.get("image_url") or ""
        # Never advertise an absent file or a fabricated floor plan as a generated result.
        image_path = Path(image_url.lstrip("/"))
        if (result.get("status") != "success" or not image_url.startswith("/static/models/")
                or not image_path.is_file() or image_path.stat().st_size == 0):
            raise HTTPException(502, result.get("message") or "이미지 생성에 실패했습니다. 사용량은 차감하지 않았습니다.")
        try:
            from PIL import Image
            with Image.open(image_path) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise ValueError("unsupported image")
                image.verify()
        except Exception:
            raise HTTPException(502, "생성된 이미지를 읽을 수 없습니다. 사용량은 차감하지 않았습니다.")
        charge_studio_trial_or_quota(user, db, request)
    can_export = user_can_export(user)
    return {
        "status": "success", "message": "AI 건축 콘셉트 이미지가 생성되었습니다. 치수가 보증된 3D 모델은 아닙니다.",
        "preview": describe_prompt_preview(prompt, "upload" if reference else "prompt"),
        "image_url": image_url, "image_provider": result.get("provider"),
        "provider_message": "AI 이미지 생성 완료. GLB/OBJ 변환은 별도 검증이 필요합니다.",
        "preview_only": not can_export, "export_locked": not can_export,
        "model_url": None, "bg_url": None, "worker_ready": False,
        "result_type": "ai_concept_image", "dimension_accurate": False,
    }


@router.post("/upload")
async def upload_floorplan(
    background_tasks: BackgroundTasks, request: Request, file: UploadFile = File(...),
    Authorization: str = Header(None), db: Session = Depends(get_db),
):
    user = get_optional_user(Authorization, db)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "JPG 또는 PNG 도면을 선택하세요.")
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "최대 10MB까지 업로드할 수 있습니다.")
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"PNG", "JPEG"} or image.width * image.height > 25_000_000:
                raise ValueError("invalid image")
            image.verify()
    except Exception:
        raise HTTPException(400, "읽을 수 있는 JPG/PNG 이미지가 아닙니다.")
    Path("uploads").mkdir(exist_ok=True)
    path = Path("uploads") / (uuid.uuid4().hex + ext)
    path.write_bytes(content)
    try:
        return await create_image_result("첨부한 평면도의 배치를 참고해 건축 콘셉트 조감 이미지를 생성해주세요.", user, db, request, str(path))
    finally:
        path.unlink(missing_ok=True)


@router.post("/generate")
async def generate_floorplan(
    background_tasks: BackgroundTasks, request: Request, prompt: str = Form(...),
    Authorization: str = Header(None), db: Session = Depends(get_db),
):
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= 4000:
        raise HTTPException(422, "프롬프트는 3~4,000자로 입력하세요.")
    user = get_optional_user(Authorization, db)
    return await create_image_result(prompt, user, db, request)
