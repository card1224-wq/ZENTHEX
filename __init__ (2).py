import os
import time
from pathlib import Path


DEFAULT_MODEL = "gemini-3.1-flash-image"


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
    inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
    if not inline_data:
        return False
    if hasattr(part, "as_image"):
        image = part.as_image()
        image.save(output_path)
        return True
    data = getattr(inline_data, "data", None)
    if isinstance(data, str):
        import base64

        output_path.write_bytes(base64.b64decode(data))
        return True
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
        return {"status": "skipped", "message": "GEMINI_API_KEY is missing, so Google AI Studio/Gemini image generation was skipped."}

    try:
        from google import genai
    except Exception as exc:
        return {
            "status": "unavailable",
            "message": f"google-genai package is unavailable, so Google AI Studio/Gemini could not be called: {exc}",
        }

    model = (
        os.getenv("ZENTHEX_GOOGLE_AI_STUDIO_MODEL")
        or os.getenv("ZENTHEX_NANOBANANA_MODEL")
        or DEFAULT_MODEL
    ).strip()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"google_ai_studio_{int(time.time())}.png"
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
                    "message": f"Google AI Studio/Gemini reference image preparation failed: {exc}",
                }

        response = client.models.generate_content(model=model, contents=contents)
        for part in _iter_response_parts(response):
            if _save_inline_image(part, output_path):
                return {
                    "status": "success",
                    "provider": "google_ai_studio",
                    "model": model,
                    "image_url": f"/static/models/{filename}",
                    "message": "Google AI Studio/Gemini 3D architectural image generated.",
                }
        return {
            "status": "empty",
            "message": "Google AI Studio/Gemini returned no image data. Check API key, model name, and image-generation access.",
        }
    except Exception as exc:
        return {"status": "error", "message": f"Google AI Studio/Gemini call failed: {exc}"}
