"""Chat system CRUD (admin only). Target systems e.g. drillquiz, cointutor."""
import logging
import os
import subprocess
import time
import jwt
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_admin_required
from app.config import get_settings
from app.database import get_db
from app.models import ChatSystem
from app.services.minio_service import (
    DEFAULT_BUCKET,
    delete_object,
    get_minio_client,
    list_objects_in_prefix,
    prefix_for_system,
    upload_files_to_bucket,
)
from app.services.system_config import get_dify_api_key, get_dify_base_url, refresh_systems_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/systems", tags=["admin-systems"])


def _require_system_owner(row: ChatSystem | None, admin_username: str) -> None:
    """Raise 403 if admin cannot access this system (not owner and not legacy)."""
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System not found")
    if row.created_by is not None and row.created_by != admin_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this system")


class SystemCreate(BaseModel):
    system_id: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field("", max_length=128)
    dify_base_url: str = Field(..., min_length=1, max_length=512)
    dify_api_key: str = Field("", max_length=256)  # Optional on create; add via edit after creating app in Dify
    dify_chatbot_token: str = Field("", max_length=128)
    allowed_origins: str = Field("", max_length=1024)
    enabled: bool = True


class SystemUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=128)
    dify_base_url: str | None = Field(None, max_length=512)
    dify_api_key: str | None = Field(None, max_length=256)
    dify_chatbot_token: str | None = Field(None, max_length=128)
    allowed_origins: str | None = Field(None, max_length=1024)
    enabled: bool | None = None


class SystemOut(BaseModel):
    id: int
    system_id: str
    display_name: str
    dify_base_url: str
    dify_api_key: str
    dify_chatbot_token: str
    allowed_origins: str
    enabled: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[SystemOut])
async def list_systems(
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """List chat systems created by the current admin."""
    result = await db.execute(
        select(ChatSystem)
        .where(
            (ChatSystem.created_by == admin_username) | (ChatSystem.created_by.is_(None))
        )
        .order_by(ChatSystem.system_id)
    )
    rows = result.scalars().all()
    return [
        SystemOut(
            id=r.id,
            system_id=r.system_id,
            display_name=r.display_name or "",
            dify_base_url=r.dify_base_url or "",
            dify_api_key=r.dify_api_key or "",
            dify_chatbot_token=r.dify_chatbot_token or "",
            allowed_origins=r.allowed_origins or "",
            enabled=r.enabled,
        )
        for r in rows
    ]


@router.post("", response_model=SystemOut, status_code=status.HTTP_201_CREATED)
async def create_system(
    body: SystemCreate,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(get_admin_required),
):
    """Create a new chat system."""
    sid = body.system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System ID already exists")
    row = ChatSystem(
        system_id=sid,
        display_name=body.display_name.strip() or sid,
        dify_base_url=body.dify_base_url.strip().rstrip("/"),
        dify_api_key=body.dify_api_key.strip(),
        dify_chatbot_token=body.dify_chatbot_token.strip(),
        allowed_origins=body.allowed_origins.strip(),
        enabled=body.enabled,
        created_by=_admin,
    )
    db.add(row)
    await db.flush()
    await refresh_systems_cache()
    return SystemOut(
        id=row.id,
        system_id=row.system_id,
        display_name=row.display_name or "",
        dify_base_url=row.dify_base_url or "",
        dify_api_key=row.dify_api_key or "",
        dify_chatbot_token=row.dify_chatbot_token or "",
        allowed_origins=row.allowed_origins or "",
        enabled=row.enabled,
    )


@router.get("/{system_id}/test-token", response_model=dict)
async def get_test_chat_token(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Issue JWT for admin to open chat page. Admin can only test systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    _require_system_owner(result.scalar_one_or_none(), admin_username)
    dify_base = get_dify_base_url(sid)
    dify_key = get_dify_api_key(sid)
    if not dify_base or not dify_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dify not configured for this system. Set dify_base_url and dify_api_key.",
        )
    settings = get_settings()
    user_id = "admin_test"
    payload = {"system_id": sid, "user_id": user_id, "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    if hasattr(token, "decode"):
        token = token.decode("utf-8")
    return {"token": token}


@router.get("/{system_id}", response_model=SystemOut)
async def get_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Get a chat system by system_id. Admin can only access systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    row = result.scalar_one_or_none()
    _require_system_owner(row, admin_username)
    return SystemOut(
        id=row.id,
        system_id=row.system_id,
        display_name=row.display_name or "",
        dify_base_url=row.dify_base_url or "",
        dify_api_key=row.dify_api_key or "",
        dify_chatbot_token=row.dify_chatbot_token or "",
        allowed_origins=row.allowed_origins or "",
        enabled=row.enabled,
    )


@router.patch("/{system_id}", response_model=SystemOut)
async def update_system(
    system_id: str,
    body: SystemUpdate,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Update a chat system. Admin can only update systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    row = result.scalar_one_or_none()
    _require_system_owner(row, admin_username)
    if body.display_name is not None:
        row.display_name = body.display_name.strip()
    if body.dify_base_url is not None:
        row.dify_base_url = body.dify_base_url.strip().rstrip("/")
    if body.dify_api_key is not None:
        row.dify_api_key = body.dify_api_key.strip()
    if body.dify_chatbot_token is not None:
        row.dify_chatbot_token = body.dify_chatbot_token.strip()
    if body.allowed_origins is not None:
        row.allowed_origins = body.allowed_origins.strip()
    if body.enabled is not None:
        row.enabled = body.enabled
    await db.flush()
    await refresh_systems_cache()
    return SystemOut(
        id=row.id,
        system_id=row.system_id,
        display_name=row.display_name or "",
        dify_base_url=row.dify_base_url or "",
        dify_api_key=row.dify_api_key or "",
        dify_chatbot_token=row.dify_chatbot_token or "",
        allowed_origins=row.allowed_origins or "",
        enabled=row.enabled,
    )


@router.post("/{system_id}/upload", response_model=dict)
async def upload_files(
    system_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """
    Upload file (or ZIP) to MinIO bucket for this system.
    Admin can only upload to systems they created.
    """
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    _require_system_owner(result.scalar_one_or_none(), admin_username)
    settings = get_settings()
    if not settings.minio_access_key or not settings.minio_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MinIO not configured (MINIO_ACCESS_KEY, MINIO_SECRET_KEY required).",
        )
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    client = get_minio_client(
        settings.minio_endpoint,
        settings.minio_port,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_use_ssl,
    )
    bucket = settings.minio_bucket or DEFAULT_BUCKET
    prefix = prefix_for_system(sid)
    data = await file.read()
    try:
        uploaded = upload_files_to_bucket(client, bucket, prefix, file.filename, data)
    except Exception as e:
        logger.exception("MinIO upload failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MinIO upload failed: {e}",
        ) from e

    return {"bucket": bucket, "uploaded": uploaded, "count": len(uploaded)}


@router.get("/{system_id}/files", response_model=list)
async def list_files(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """List files in rag-docs/raw/{system_id}/. Admin can only list systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    _require_system_owner(result.scalar_one_or_none(), admin_username)
    settings = get_settings()
    if not settings.minio_access_key or not settings.minio_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MinIO not configured.",
        )
    client = get_minio_client(
        settings.minio_endpoint,
        settings.minio_port,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_use_ssl,
    )
    bucket = settings.minio_bucket or DEFAULT_BUCKET
    prefix = prefix_for_system(sid)
    try:
        items = list_objects_in_prefix(client, bucket, prefix)
    except Exception as e:
        logger.exception("MinIO list failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MinIO list failed: {e}",
        ) from e
    return items


@router.delete("/{system_id}/files", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    system_id: str,
    key: str = Query(..., description="Object key e.g. raw/drillquiz/USECASE.md"),
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Delete file in rag-docs/raw/{system_id}/. Admin can only delete in systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    _require_system_owner(result.scalar_one_or_none(), admin_username)
    settings = get_settings()
    if not settings.minio_access_key or not settings.minio_secret_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MinIO not configured.")
    client = get_minio_client(
        settings.minio_endpoint,
        settings.minio_port,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_use_ssl,
    )
    bucket = settings.minio_bucket or DEFAULT_BUCKET
    prefix = prefix_for_system(sid)
    try:
        delete_object(client, bucket, key, prefix)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("MinIO delete failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MinIO delete failed: {e}",
        ) from e


@router.post("/{system_id}/trigger-reindex", response_model=dict)
async def trigger_reindex(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Trigger RAG ingestion Job. Admin can only trigger for systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    _require_system_owner(result.scalar_one_or_none(), admin_username)
    job_name = f"ingest-{sid}-{int(time.time())}"
    cronjob_name = f"rag-ingestion-cronjob-{sid}"
    namespace = "rag"
    env = os.environ.copy()
    try:
        result = subprocess.run(
            ["kubectl", "create", "job", "-n", namespace, job_name, f"--from=cronjob/{cronjob_name}"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"kubectl failed: {err}",
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="kubectl timed out",
        ) from None
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="kubectl not found. Ensure kubectl is installed and in PATH.",
        ) from None
    except Exception as e:
        logger.exception("trigger-reindex failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"trigger-reindex failed: {e}",
        ) from e
    return {"job_name": job_name}


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Delete a chat system. Admin can only delete systems they created."""
    sid = system_id.strip().lower()
    result = await db.execute(select(ChatSystem).where(ChatSystem.system_id == sid))
    row = result.scalar_one_or_none()
    _require_system_owner(row, admin_username)
    await db.delete(row)
    await refresh_systems_cache()
