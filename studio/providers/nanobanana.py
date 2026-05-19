import os
import time
from pathlib import Path


DEFAULT_MODEL = "gemini-2.5-flash-image"


def is_configured() -> bool:
    return bool((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip())


def _iter_response_parts(response):
    parts = getattr(response, "parts", None)
    if parts:
        yield from parts
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            yield part


def _save_inline_image(part, output_path: Path) -> bool:
    inline_data = getattr(part, "inline_data", None)
    if not inline_data:
        return False
    if hasattr(part, "as_image"):
        image = part.as_image()
        image.save(output_path)
        return True
    data = getattr(inline_data, "data", None)
    if data:
        output_path.write_bytes(data)
        return True
    return False


def generate_preview_image(prompt: str, output_dir: str = "static/models") -> dict:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        return {"status": "skipped", "message": "GEMINI_API_KEY가 없어 NanoBanana/Gemini 이미지 생성을 건너뛰었습니다."}

    try:
        from google import genai
    except Exception as exc:
        return {
            "status": "unavailable",
            "message": f"google-genai 패키지가 없어 NanoBanana/Gemini를 호출하지 못했습니다: {exc}",
        }

    model = (os.getenv("ZENTHEX_NANOBANANA_MODEL") or DEFAULT_MODEL).strip()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"nanobanana_{int(time.time())}.png"
    output_path = Path(output_dir) / filename

    studio_prompt = (
        "Create a polished architectural concept render for Zenthex Studio. "
        "Use a clean premium SaaS visual style, realistic spatial composition, "
        "clear room zoning, modern Korean residential/interior design taste, "
        "architectural lighting, and no text labels. "
        f"User request: {prompt}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=[studio_prompt])
        for part in _iter_response_parts(response):
            if _save_inline_image(part, output_path):
                return {
                    "status": "success",
                    "provider": "nanobanana",
                    "model": model,
                    "image_url": f"/static/models/{filename}",
                    "message": "NanoBanana/Gemini 이미지 생성 완료",
                }
        return {
            "status": "empty",
            "message": "NanoBanana/Gemini 응답에 이미지 데이터가 없습니다. API 키, 모델명, 이미지 생성 권한을 확인하세요.",
        }
    except Exception as exc:
        return {"status": "error", "message": f"NanoBanana/Gemini 호출 실패: {exc}"}
