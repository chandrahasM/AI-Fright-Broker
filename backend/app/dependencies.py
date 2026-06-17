from functools import lru_cache

from openai import OpenAI
from supabase import Client, create_client

from app.config import settings
from app.repositories.carrier_repository import CarrierRepository
from app.repositories.draft_repository import DraftRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository
from app.repositories.voice_repository import VoiceRepository


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def get_email_repository() -> EmailRepository:
    return EmailRepository(get_supabase_client())


def get_carrier_repository() -> CarrierRepository:
    return CarrierRepository(get_supabase_client())


def get_load_repository() -> LoadRepository:
    return LoadRepository(get_supabase_client())


def get_interaction_repository() -> InteractionRepository:
    return InteractionRepository(get_supabase_client())


def get_draft_repository() -> DraftRepository:
    return DraftRepository(get_supabase_client())


def get_rate_history_repository() -> RateHistoryRepository:
    return RateHistoryRepository(get_supabase_client())


def get_voice_repository() -> VoiceRepository:
    return VoiceRepository(get_supabase_client())
