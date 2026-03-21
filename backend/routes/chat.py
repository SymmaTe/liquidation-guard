"""
对话历史接口：
- GET    /chat/{wallet}                        — 获取对话列表
- POST   /chat/{wallet}                        — 新建对话
- DELETE /chat/{wallet}/{conversation_id}      — 删除对话
- GET    /chat/{wallet}/{conversation_id}      — 获取对话消息
- POST   /chat/{wallet}/{conversation_id}      — 追加消息
"""

from fastapi import APIRouter
from pydantic import BaseModel
from db import supabase

router = APIRouter()


class NewConversation(BaseModel):
    title: str


class NewMessage(BaseModel):
    role: str   # user | assistant
    content: str


# ─── 对话列表 ─────────────────────────────────────────────────────────────────

@router.get("/{wallet}")
async def list_conversations(wallet: str):
    try:
        res = (
            supabase.table("chat_conversations")
            .select("id, title, created_at, updated_at")
            .eq("wallet_address", wallet)
            .order("updated_at", desc=True)
            .execute()
        )
        return {"ok": True, "data": res.data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/{wallet}")
async def create_conversation(wallet: str, body: NewConversation):
    try:
        res = (
            supabase.table("chat_conversations")
            .insert({"wallet_address": wallet, "title": body.title})
            .execute()
        )
        return {"ok": True, "data": res.data[0]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.delete("/{wallet}/{conversation_id}")
async def delete_conversation(wallet: str, conversation_id: str):
    try:
        supabase.table("chat_conversations").delete().eq("id", conversation_id).eq("wallet_address", wallet).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 消息 ─────────────────────────────────────────────────────────────────────

@router.get("/{wallet}/{conversation_id}")
async def get_messages(wallet: str, conversation_id: str):
    try:
        res = (
            supabase.table("chat_messages")
            .select("id, role, content, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return {"ok": True, "data": res.data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/{wallet}/{conversation_id}")
async def add_message(wallet: str, conversation_id: str, body: NewMessage):
    try:
        # 插入消息
        res = (
            supabase.table("chat_messages")
            .insert({"conversation_id": conversation_id, "role": body.role, "content": body.content})
            .execute()
        )
        # 第一条用户消息自动更新标题
        update_fields: dict = {"updated_at": "now()"}
        if body.role == "user":
            existing = (
                supabase.table("chat_messages")
                .select("id")
                .eq("conversation_id", conversation_id)
                .eq("role", "user")
                .execute()
            )
            if len(existing.data) == 1:   # 刚插入的这条是第一条
                title = body.content[:20] + ("…" if len(body.content) > 20 else "")
                update_fields["title"] = title
        supabase.table("chat_conversations").update(update_fields).eq("id", conversation_id).execute()
        return {"ok": True, "data": res.data[0]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
