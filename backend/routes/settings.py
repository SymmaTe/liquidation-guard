"""
用户设置接口：
- GET  /settings/{wallet}  — 读取用户设置
- POST /settings/{wallet}  — 保存用户设置
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from db import supabase

router = APIRouter()


class UserSettings(BaseModel):
    monitor_enabled: bool = False
    monitor_addresses: list[str] = []
    refresh_interval: int = 300
    warning_hf: float = 1.4
    danger_hf: float = 1.1
    custom_thresholds: bool = False
    telegram_chat_id: str = ''
    alert_cooldown_warning: int = 30
    alert_cooldown_danger: int = 5
    rpc_url: str = ''
    ai_provider: str = 'anthropic'
    ai_model: str = ''
    ai_api_key: str = ''


@router.get("/{wallet}")
async def get_settings(wallet: str):
    try:
        res = supabase.table("user_settings").select("*").eq("wallet_address", wallet).single().execute()
        return {"ok": True, "data": res.data}
    except Exception:
        return {"ok": False, "data": None}


@router.post("/{wallet}")
async def save_settings(wallet: str, body: UserSettings):
    try:
        data = {
            "wallet_address": wallet,
            **body.model_dump(),
            "updated_at": "now()",
        }
        supabase.table("user_settings").upsert(data).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
