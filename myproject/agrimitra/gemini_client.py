import io
from typing import Optional, Tuple, List, Dict

from django.conf import settings

# Lazy import holder
genai = None  # will be imported in _ensure_client()


SYSTEM_INSTRUCTION = (
    "You are Krishi Mitra, a helpful agricultural assistant for Indian farmers. "
    "Answer clearly and concisely. If the user's message is in an Indian language, respond in that same language. "
    "If an image is provided, analyze it and incorporate visual details into your answer. "
    "When relevant, provide practical, location-agnostic guidance and safety notes."
)


def _ensure_client():
    global genai
    if genai is None:
        try:
            import google.generativeai as _genai
            genai = _genai
        except Exception as e:  # pragma: no cover
            import sys
            raise RuntimeError(
                "google-generativeai is not available in this Python environment.\n"
                f"Interpreter: {sys.executable}\n"
                "Fix: Activate your virtualenv and run 'pip install google-generativeai', then start the server from that same env.\n"
                f"Details: {e}"
            )
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not configured. Set it in environment or settings.py."
        )
    genai.configure(api_key=api_key)


def _model_candidates() -> list[str]:
    # Preferred model can be set via settings; otherwise try fallbacks
    preferred = getattr(settings, 'GEMINI_MODEL', '') or ''
    fallbacks = [
        'gemini-pro-vision',
        'gemini-1.0-pro-vision',
        'gemini-1.0-pro-vision-latest',
        'gemini-1.5-flash-8b',
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-1.5-pro-latest',
    ]
    if preferred and preferred not in fallbacks:
        return [preferred] + fallbacks
    return [preferred] + [m for m in fallbacks if m != preferred]


def _image_part_from_django_file(f) -> Optional[dict]:
    if not f:
        return None
    # Ensure file is read into bytes; Django may give InMemoryUploadedFile or TemporaryUploadedFile
    data = f.read()
    # Reset pointer for any further use
    try:
        f.seek(0)
    except Exception:
        pass
    mime = getattr(f, 'content_type', None) or 'application/octet-stream'
    return {"inline_data": {"mime_type": mime, "data": data}}


def ask_gemini(message: str, image_file=None, language: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, dict]:
    """
    Ask Gemini with a text prompt and optional image.

    Returns: (text_response, raw_response_dict)
    Raises RuntimeError on configuration or API errors.
    """
    _ensure_client()

    parts = []
    # Language steering: force output language if provided (e.g., 'Hindi', 'hi')
    if language:
        parts.append(f"Important: Respond ONLY in {language}. If the user writes in another language, translate and answer strictly in {language}.")

    # Include short history for context (user/assistant alternating), newest last
    if history:
        for turn in history[-8:]:
            r = (turn.get('role') or '').lower()
            t = (turn.get('text') or '').strip()
            if not t:
                continue
            prefix = 'User:' if r == 'user' else 'Assistant:' if r == 'assistant' else ''
            parts.append(f"{prefix} {t}" if prefix else t)
    img_part = _image_part_from_django_file(image_file)
    # If only image provided, add a helpful default prompt
    if (not message) and img_part:
        message = (
            "Analyze this image and provide agriculture-related insights. "
            "Identify crops, diseases or pests if visible, and suggest practical next steps."
        )
    if message:
        parts.append(message.strip())
    if img_part:
        parts.append(img_part)

    if not parts:
        raise RuntimeError("Empty prompt: provide text or an image.")

    last_err = None
    tried = []
    for model_name in _model_candidates():
        if not model_name:
            continue
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                },
            )
            resp = model.generate_content(parts)
            text = getattr(resp, 'text', None) or ""
            if not text:
                try:
                    for cand in (resp.candidates or []):
                        for part in (cand.content.parts or []):
                            if getattr(part, 'text', None):
                                text += part.text
                except Exception:
                    pass
            return (text or ""), getattr(resp, 'to_dict', lambda: {} )()
        except Exception as e:  # pragma: no cover
            tried.append(model_name)
            # If model not found/unsupported, try next; otherwise break
            msg = str(e).lower()
            last_err = e
            # If image not supported by this model, try text-only fallback once
            if img_part and ('image' in msg or 'inline_data' in msg or 'inlinedata' in msg):
                try:
                    resp = model.generate_content([p for p in parts if isinstance(p, str) and p])
                    text = getattr(resp, 'text', None) or ""
                    if not text:
                        try:
                            for cand in (resp.candidates or []):
                                for part in (cand.content.parts or []):
                                    if getattr(part, 'text', None):
                                        text += part.text
                        except Exception:
                            pass
                    return (text or ""), getattr(resp, 'to_dict', lambda: {} )()
                except Exception as e2:  # pragma: no cover
                    last_err = e2
                    msg = str(e2).lower()
            if 'not found' in msg or '404' in msg or 'not supported' in msg:
                continue
            break

    # Dynamic discovery fallback: list models available to the key and try those supporting generateContent
    try:
        models = list(genai.list_models())
    except Exception as e:  # pragma: no cover
        models = []
        last_err = last_err or e
    if models:
        dyn_names = []
        for m in models:
            name = getattr(m, 'name', '')
            methods = list(getattr(m, 'supported_generation_methods', []) or [])
            if 'generateContent' in methods or 'generate_content' in [s.lower() for s in methods]:
                dyn_names.append(name)
        # Prefer multimodal-looking names if an image was provided
        if img_part:
            dyn_names.sort(key=lambda n: (('vision' not in n and '1.5' not in n), n))
        else:
            dyn_names.sort()
        for model_name in dyn_names:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION,
                    generation_config={
                        "temperature": 0.6,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 2048,
                    },
                )
                resp = model.generate_content(parts)
                text = getattr(resp, 'text', None) or ""
                if not text:
                    try:
                        for cand in (resp.candidates or []):
                            for part in (cand.content.parts or []):
                                if getattr(part, 'text', None):
                                    text += part.text
                    except Exception:
                        pass
                return (text or ""), getattr(resp, 'to_dict', lambda: {} )()
            except Exception as e:  # pragma: no cover
                tried.append(model_name)
                last_err = e
                continue

    # If we got here, all candidates failed
    cand_str = ", ".join([m for m in _model_candidates() if m])
    tried_str = ", ".join(tried) if tried else cand_str
    raise RuntimeError(
        "Gemini API error: no compatible model found.\n"
        f"Tried models: {tried_str}\n"
        "Tip: run 'python manage.py list_gemini_models' and set GEMINI_MODEL to a model that supports generateContent.\n"
        f"Last error: {last_err}"
    )
