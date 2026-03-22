"""
用户设置接口：
- GET  /settings/{wallet}  — 读取用户设置
- POST /settings/{wallet}  — 保存用户设置
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from db import supabase
from crypto import encrypt, decrypt

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
        data = res.data or {}
        # Don't expose ai_api_key to frontend; return has_ai_key flag instead
        raw_key = data.pop("ai_api_key", "") or ""
        data["has_ai_key"] = bool(raw_key)
        return {"ok": True, "data": data}
    except Exception:
        return {"ok": False, "data": None}


@router.post("/{wallet}")
async def save_settings(wallet: str, body: UserSettings):
    # Validate thresholds
    if body.custom_thresholds and body.danger_hf >= body.warning_hf:
        return {"ok": False, "error": "紧急线必须低于注意线"}
    if body.monitor_enabled and not body.monitor_addresses:
        return {"ok": False, "error": "开启监控时至少需要一个监控地址"}
    try:
        data = body.model_dump()
        # Encrypt api key; if empty string sent, keep existing key (don't overwrite with empty)
        raw_key = data.get("ai_api_key", "")
        if raw_key:
            data["ai_api_key"] = encrypt(raw_key)
        else:
            # Don't overwrite existing key with empty
            data.pop("ai_api_key", None)
        data = {
            "wallet_address": wallet,
            **data,
            "updated_at": "now()",
        }
        supabase.table("user_settings").upsert(data).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
