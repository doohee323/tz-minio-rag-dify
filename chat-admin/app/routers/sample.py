"""Sample code download (admin only)."""
import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.auth import get_admin_required

router = APIRouter(prefix="/v1/admin", tags=["admin-sample"])

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample"


@router.get("/sample/download", response_class=Response)
async def download_sample_zip(_admin: str = Depends(get_admin_required)):
    """Download chat-admin/sample as a zip file."""
    if not SAMPLE_DIR.exists():
        return Response(content=b"Sample directory not found", status_code=404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in SAMPLE_DIR.rglob("*"):
            if f.is_file():
                arcname = f.relative_to(SAMPLE_DIR)
                zf.write(f, arcname)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=chat-admin-sample.zip"},
    )
