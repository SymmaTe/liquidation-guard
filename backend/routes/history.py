"""
健康历史接口：
GET /history/{address} — 查询某地址的健康度历史（最近 7 天）
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from db import supabase

router = APIRouter()


@router.get("/{address}")
async def get_health_history(address: str, days: int = 7):
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            supabase.table("health_history")
            .select("health_factor,collateral_usd,debt_usd,alert_level,recorded_at")
            .eq("monitored_address", address)
            .gte("recorded_at", cutoff)
            .order("recorded_at", desc=True)
            .limit(5000)
            .execute()
        )
        result.data.reverse()
        return {"ok": True, "data": result.data}
    except Exception as e:
        return {"ok": False, "error": str(e)}
