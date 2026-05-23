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


def _build_studio_prompt(prompt: str, has_reference: bool) -> str:
    reference_note = (
        "Use the attached reference image as the source layout and transform it into a polished 3D floor-plan render. "
        if has_reference
        else ""
    )
    return (
        "Create the main Zenthex Studio result as a premium isometric 3D architectural floor-plan image. "
        "The result should look like a detailed top-down 3D apartment or interior model: visible walls, rooms, "
        "furniture, wood floors, windows, balconies, bathrooms, kitchen, lighting, and realistic depth. "
        "If the user asks for a Korean apartment, use a modern Korean residential layout and Korean room labels "
        "only where they help explain the floor plan. Do not create a flat 2D blueprint. Do not create abstract art. "
        "Make it presentation-ready for a SaaS customer who wants to preview the space before subscribing. "
        f"{reference_note}User request: {prompt}"
    )


def generate_preview_image(prompt: str, output_dir: str = "static/models", reference_image_path: str | None = None) -> dict:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        return {"status": "skipped", "message": "GEMINI_API_KEY가 없어 NanoBanana/Gemini 3D 이미지 생성을 건너뛰었습니다."}

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
    studio_prompt = _build_studio_prompt(prompt, bool(reference_image_path))

    try:
        client = genai.Client(api_key=api_key)
        contents = [studio_prompt]
        if reference_image_path:
            try:
                from google.genai import types

                path = Path(reference_image_path)
                suffix = path.suffix.lower()
                mime_type = "image/png" if suffix == ".png" else "image/jpeg"
                contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type))
            except Exception as exc:
                return {
                    "status": "error",
                    "message": f"NanoBanana/Gemini 참고 이미지 준비 실패: {exc}",
                }

        response = client.models.generate_content(model=model, contents=contents)
        for part in _iter_response_parts(response):
            if _save_inline_image(part, output_path):
                return {
                    "status": "success",
                    "provider": "nanobanana",
                    "model": model,
                    "image_url": f"/static/models/{filename}",
                    "message": "NanoBanana/Gemini 3D 건축 이미지 생성 완료",
                }
        return {
            "status": "empty",
            "message": "NanoBanana/Gemini 응답에 이미지 데이터가 없습니다. API 키, 모델명, 이미지 생성 권한을 확인하세요.",
        }
    except Exception as exc:
        return {"status": "error", "message": f"NanoBanana/Gemini 호출 실패: {exc}"}
