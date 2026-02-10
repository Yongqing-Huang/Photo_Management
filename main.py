import os
from pathlib import Path

from db import *
from photo_processing import *
from metadata_preprocessing import *


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def ingest_photo(photo: str, web_path: str, thumb_path: str, metadata_path: str):
    sha256 = sha256_file(photo)
    existing_id = get_photo_id_by_sha256(sha256)

    if existing_id:
        # print(f"Skip ALL processing (duplicate): {photo}")
        return None

    xmp_str = get_xmp_str(photo)
    export_metadata_to_txt(photo, metadata_path)
    field = extract_xmp_fields(xmp_str)
    normalized_field = normalize_xmp_fields(field)

    export_web_jpg(photo, web_path)
    export_thumb_jpg(photo, thumb_path)

    photo_id = insert_full_metadata(photo, normalized_field)
    return photo_id


def iter_files_recursive(root: Path):
    """Yield all files under root recursively, skipping hidden files."""
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith("."):
                continue
            yield Path(dirpath) / name


def main():
    # Read from .env
    photos_root = Path(os.getenv("PHOTOS_ROOT"))
    exports_root = Path(os.getenv("EXPORTS_ROOT"))

    web_dir = exports_root / "Web"
    thumb_dir = exports_root / "Thumb"
    metadata_dir = exports_root / "Metadata"

    # Extension filter
    exts_raw = os.getenv("INGEST_EXTS", "")
    allowed_exts = {e.strip().lower() for e in exts_raw.split(",") if e.strip()}

    for path in iter_files_recursive(photos_root):
        if allowed_exts and path.suffix.lower() not in allowed_exts:
            continue

        ingest_photo(
            str(path),
            web_path=str(web_dir),
            thumb_path=str(thumb_dir),
            metadata_path=str(metadata_dir),
        )


if __name__ == "__main__":
    main()









