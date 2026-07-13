"""
lib/llm.py — the LLM translation call.
Turns an English string into Mexican Spanish (es-MX) via Claude.

FAIL LOUD: no try/except that returns `text` on error. If the provider fails,
let the exception propagate so the gateway returns a 502.
"""
import os

from anthropic import AsyncAnthropic

MODEL_DEFAULT = os.getenv("MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are a professional localizer translating English website and "
    "e-commerce UI text into natural Mexican Spanish (es-MX).\n"
    "Rules:\n"
    "- Use native es-MX vocabulary and grammar: 'computadora' (not 'ordenador'), "
    "'carro' (not 'coche'), 'celular' (not 'móvil'), 'agregar al carrito' "
    "(not 'añadir a la cesta'). Use 'ustedes', never 'vosotros'.\n"
    "- The input is a short UI string (nav label, button, heading, product "
    "name, or price). Translate it as interface copy.\n"
    "- Preserve EXACTLY: numbers, prices and currency symbols, SKUs, "
    "model/product codes, brand names, URLs, and email addresses.\n"
    "- Return ONLY the translation — no preamble, no explanation, no surrounding quotes.\n"
    "- If there is nothing to translate (a bare number, code, or already-Spanish "
    "text), return the input unchanged."
)

# Reuse one client across calls (connection pooling → better throughput).
# Built lazily so construction happens AFTER app.py's load_dotenv() sets
# ANTHROPIC_API_KEY — imports run before load_dotenv().
_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY
    return _client


async def translate_text(text: str, target: str = "es-MX", model: str = MODEL_DEFAULT) -> str:
    """Return `text` translated into Mexican Spanish. (`target` is es-MX only for now.)"""
    msg = await _get_client().messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return msg.content[0].text.strip()
