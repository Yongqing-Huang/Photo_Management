import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

from db import *
from photo_processing import *
from metadata_preprocessing import *

# --- Logging Setup (file only) ---
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"{now_str}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# --- End Logging Setup ---


def ingest_photo(conn, photo: str, web_path: str, thumb_path: str, metadata_path: str):
    existing_path_id = get_photo_id_by_path(conn, photo)

    if existing_path_id is not None:
        new_sha = sha256_file(photo)
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
    new_sha = sha256_file(photo)
    existing_sha_id = get_photo_id_by_sha256(conn, new_sha)

    if existing_sha_id is not None:
        existing_path = get_photo_path_by_id(conn, existing_sha_id)

        logging.info("Duplicate content found under different path")
        logging.info(f"New path: {photo}")
        logging.info(f"Existing path in DB: {existing_path}")

        return 0, 0, 1, 0

    try:
        xmp_str = get_xmp_str(photo)
    except Exception as e:
        raise RuntimeError(f"get_xmp_str failed: {e}")

    try:
        export_metadata_to_txt(photo, metadata_path)
    except Exception as e:
        raise RuntimeError(f"export_metadata_to_txt failed: {e}")

    field = extract_xmp_fields(xmp_str)
    normalized_field = normalize_xmp_fields(field)

    try:
        export_web_jpg(photo, web_path)
    except Exception as e:
        raise RuntimeError(f"export_web_jpg failed: {e}")

    try:
        export_thumb_jpg(photo, thumb_path)
    except Exception as e:
        raise RuntimeError(f"export_thumb_jpg failed: {e}")

    try:
        insert_full_metadata(conn, photo, normalized_field)
    except Exception as e:
        raise RuntimeError(f"insert_full_metadata failed: {e}")

    return 0, 0, 0, 1


def iter_files_recursive(root: Path):
    """Yield all files under root recursively, skipping hidden files."""
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith("."):
                continue
            yield Path(dirpath) / name


def main():
    # Read from .env
    total = 0
    inserted = 0
    skipped_path_match = 0
    skipped_duplicate = 0
    changed = 0
    failed = 0

    # DB must work or exit
    try:
        conn = get_connection()
    except Exception as e:
        logging.error(f"DB connection failed: {e}")
        sys.exit(1)


    try:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            logging.error("Environment variables not set.")
            sys.exit(1)

        # Validate config
        photos_root_raw = os.getenv("PHOTOS_ROOT")
        if not photos_root_raw:
            logging.error("PHOTOS_ROOT not set")
            sys.exit(1)

        photos_root = Path(photos_root_raw)
        exports_root = Path(os.getenv("EXPORTS_ROOT"))

        web_dir = exports_root / "Web"
        thumb_dir = exports_root / "Thumb"
        metadata_dir = exports_root / "Metadata"
        exts_raw = os.getenv("INGEST_EXTS", "")
        allowed_exts = {e.strip().lower() for e in exts_raw.split(",") if e.strip()}

        # Now process files
        for path in iter_files_recursive(photos_root):
            total += 1
            try:
                if allowed_exts and path.suffix.lower() not in allowed_exts:
                    continue
                d_skip_match, d_changed, d_dup, d_inserted = ingest_photo(
                    conn,
                    str(path),
                    web_path=str(web_dir),
                    thumb_path=str(thumb_dir),
                    metadata_path=str(metadata_dir),
                )

                skipped_path_match += d_skip_match
                changed += d_changed
                skipped_duplicate += d_dup
                inserted += d_inserted
            except Exception as e:
                logging.error(f"Failed processing {path}: {e}")
                failed += 1

        # Write to log
        logging.info("=== Ingest Summary ===")
        logging.info(f"Total scanned: {total}")
        logging.info(f"Inserted: {inserted}")
        logging.info(f"Skipped (path+sha match): {skipped_path_match}")
        logging.info(f"Skipped (duplicate content): {skipped_duplicate}")
        logging.info(f"Content changed: {changed}")
        logging.info(f"Failed: {failed}")

        # Print Results
        print("=== Ingest Summary ===")
        print(f"Total scanned: {total}")
        print(f"Inserted: {inserted}")
        print(f"Skipped (path+sha match): {skipped_path_match}")
        print(f"Skipped (duplicate content): {skipped_duplicate}")
        print(f"Content changed: {changed}")
        print(f"Failed: {failed}")
        print(f"Log saved to: {LOG_FILE}")
    finally:
        conn.close()



if __name__ == "__main__":
    main()









