"""
MinIO upload service for RAG documents.
Path: rag-docs/raw/{system_id}/filename  (single bucket, system_id subfolder)
Ref: tz-minio-rag-dify/rag/scripts/ingest.py, tz-drillquiz (boto3 put_object)
"""
import io
import zipfile
from typing import Generator

from minio import Minio

DEFAULT_BUCKET = "rag-docs"


def get_minio_client(endpoint: str, port: int, access_key: str, secret_key: str, use_ssl: bool) -> Minio:
    """Create MinIO client. Ref: tz-minio-rag-dify rag/scripts/ingest.py"""
    return Minio(
        f"{endpoint}:{port}",
        access_key=access_key,
        secret_key=secret_key,
        secure=use_ssl,
    )


def prefix_for_system(system_id: str) -> str:
    """Path prefix: raw/{system_id}/ → e.g. raw/drillquiz/"""
    sid = system_id.strip().lower()
    return f"raw/{sid}/"


def ensure_bucket(client: Minio, bucket: str) -> None:
    """Create bucket if it does not exist. Ref: tz-minio-rag-dify ingest.py."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def list_objects_in_prefix(client: Minio, bucket: str, prefix: str) -> list[dict]:
    """List objects under prefix. Returns [{object_name, size, last_modified}, ...]. Folders excluded.
    Path: bucket=rag-docs, prefix=raw/drillquiz/ -> lists rag-docs/raw/drillquiz/*"""
    prefix = prefix.rstrip("/") + "/" if prefix else ""
    out: list[dict] = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        if obj.object_name.endswith("/"):
            continue
        size = obj.size if isinstance(obj.size, int) else getattr(obj.size, "value", 0)
        out.append({
            "object_name": obj.object_name,
            "filename": obj.object_name[len(prefix):] if obj.object_name.startswith(prefix) else obj.object_name,
            "size": size,
            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
        })
    return out


def delete_object(client: Minio, bucket: str, object_name: str, allowed_prefix: str) -> None:
    """
    Delete object. Ensures object_name starts with allowed_prefix (e.g. raw/drillquiz/) to prevent escaping.
    """
    prefix = allowed_prefix.rstrip("/") + "/"
    if not object_name.startswith(prefix):
        raise ValueError(f"Object key must be under {prefix}")
    client.remove_object(bucket, object_name)


def upload_file(
    client: Minio,
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload bytes to MinIO. Same object_name overwrites (S3 behavior).
    Ref: tz-drillquiz put_object(Bucket, Key, Body, ContentType).
    """
    stream = io.BytesIO(data)
    length = len(data)
    client.put_object(bucket, object_name, stream, length, content_type=content_type)
    return object_name


def content_type_for_filename(filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    mime = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
        "json": "application/json",
        "html": "text/html",
        "csv": "text/csv",
    }
    return mime.get(ext, "application/octet-stream")


def _iter_zip_files(zip_bytes: bytes) -> Generator[tuple[str, bytes], None, None]:
    """Yield (path_in_archive, file_bytes) for each non-directory entry in ZIP."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # Skip hidden / absolute paths
            name = info.filename.lstrip("/")
            if name.startswith(".") or ".." in name:
                continue
            yield name, zf.read(info)


def upload_files_to_bucket(
    client: Minio,
    bucket: str,
    prefix: str,
    filename: str,
    file_bytes: bytes,
) -> list[str]:
    """
    Upload a file to bucket. If ZIP, extract and upload each file under prefix.
    Same name overwrites. Returns list of object keys uploaded.
    Target path: {bucket}/{prefix}{filename} e.g. rag-docs/raw/drillquiz/USECASE.md
    """
    ensure_bucket(client, bucket)
    prefix = prefix.rstrip("/") + "/" if prefix else ""
    uploaded: list[str] = []

    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    if ext == "zip":
        for path_in_zip, data in _iter_zip_files(file_bytes):
            key = prefix + path_in_zip
            ct = content_type_for_filename(path_in_zip)
            upload_file(client, bucket, key, data, content_type=ct)
            uploaded.append(key)
    else:
        key = prefix + filename
        ct = content_type_for_filename(filename)
        upload_file(client, bucket, key, file_bytes, content_type=ct)
        uploaded.append(key)

    return uploaded
