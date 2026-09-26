from pathlib import Path
import logging

from src.photo_management.photo_processing import *
from src.photo_management.metadata_preprocessing import *
from src.photo_management.db import *

def ingest_photo(
        conn,
        photo: str,
        web_path: str,
        thumb_path: str,
        metadata_path: str
):
    existing_path_id = get_photo_id_by_path(conn, photo)
    new_sha = sha256_file(photo)

    if existing_path_id is not None:
        stored_sha = get_photo_sha256_by_path(conn, photo)

        if new_sha == stored_sha:
            # logging.info(f"Skip (path + sha match): {photo}")
            return 1, 0, 0, 0

        logging.warning("Content changed for existing path")
        logging.warning(f"DB path: {photo}")
        logging.warning(f"Old sha256: {stored_sha}")
        logging.warning(f"New sha256: {new_sha}")

        return 0, 1, 0, 0 # Just log, do nothing

    # Path not found — check duplicate content elsewhere
    existing_sha_id = get_photo_id_by_sha256(conn, new_sha)

    if existing_sha_id is not None:
        existing_path = get_photo_path_by_id(conn, existing_sha_id)

        logging.info("Duplicate content found under different path")
        logging.info(f"New path: {photo}")
        logging.info(f"Existing path in DB: {existing_path}")

        return 0, 0, 1, 0

    # Extract + merge + normalize EXIF/XMP metadata
    try:
        metadata = extract_metadata(photo)
    except Exception as e:
        raise RuntimeError(f"extract_metadata failed: {e}") from e

    # Export raw metadata
    try:
        export_metadata_to_txt(photo, metadata_path)
    except Exception as e:
        raise RuntimeError(f"export_metadata_to_txt failed: {e}")

    # Generate web image
    try:
        export_web_jpg(photo, web_path)
    except Exception as e:
        raise RuntimeError(f"export_web_jpg failed: {e}")

    # Generate thumbnail
    try:
        export_thumb_jpg(photo, thumb_path)
    except Exception as e:
        raise RuntimeError(f"export_thumb_jpg failed: {e}")

    src = Path(photo)
    web_out = Path(web_path) / (src.stem + ".jpg")
    thumb_out = Path(thumb_path) / (src.stem + ".jpg")

    variant_paths = {
        "web": {"path": str(web_out)},
        "thumb": {"path": str(thumb_out)},
    }


    try:
        insert_full_metadata(conn, photo, metadata, variant_paths=variant_paths)
    except Exception as e:
        raise RuntimeError(f"insert_full_metadata failed: {e}")

    return 0, 0, 0, 1