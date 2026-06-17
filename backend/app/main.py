import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import emails, drafts, chat, voice

# ── Logging setup ──────────────────────────────────────────────────────────────
# Console  → INFO  (clean summary lines only)
# File     → DEBUG (full prompts, tool payloads, token counts, draft text)
#
# Third-party libraries (httpcore, httpx, hpack, uvicorn, openai, supabase)
# are capped at WARNING so they never pollute the log file.
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "agent.log"

_fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s - %(message)s")

_file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

# Root logger: WARNING — stops third-party noise from ever reaching handlers
logging.basicConfig(level=logging.WARNING, handlers=[_file_handler, _console_handler])

# Our app loggers: DEBUG to file, INFO to console
_APP_LOGGERS = [
    "app.agent.agent",
    "app.agent.tools",
    "app.services.email_processing_service",
    "app.routers.emails",
    "app.routers.drafts",
    "app.routers.chat",
    "app.routers.voice",
    "app.services.voice_processing_service",
]
for _name in _APP_LOGGERS:
    _log = logging.getLogger(_name)
    _log.setLevel(logging.DEBUG)

    _fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    _fh.setFormatter(_fmt)
    _fh.setLevel(logging.DEBUG)
    _log.addHandler(_fh)

    _ch = logging.StreamHandler()
    _ch.setFormatter(_fmt)
    _ch.setLevel(logging.INFO)
    _log.addHandler(_ch)

    _log.propagate = False  # don't bubble up to the root WARNING handler

app = FastAPI(
    title="Goodlane Freight Broker Inbox API",
    version="1.0.0",
    description="AI-powered inbox assistant for freight brokers",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production to your Vercel domain
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(voice.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
