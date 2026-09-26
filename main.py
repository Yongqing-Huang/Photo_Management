import os
import sys
from tqdm import tqdm
import logging

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.photo_management.db import get_connection
from src.photo_management.ingest import ingest_photo

# Logging Setup
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



def iter_files_recursive(root: Path):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith("."):
                continue
            yield Path(dirpath) / name


def main():
    # r
    total = 0
    inserted = 0
    skipped_path_match = 0
    skipped_duplicate = 0
    changed = 0
    failed = 0

    # Load environment
    try:
        load_dotenv()
    except Exception:
        logging.error("Environment variables not set.")
        sys.exit(1)

    # Validate config
    photos_root_raw = os.getenv("PHOTOS_ROOT")
    if not photos_root_raw:
        logging.error("PHOTOS_ROOT not set")
        sys.exit(1)

    photos_root_raw = os.getenv("PHOTOS_ROOT")
    exports_root_raw = os.getenv("EXPORTS_ROOT")

    if not photos_root_raw:
        logging.error("PHOTOS_ROOT not set")
        sys.exit(1)

    if not exports_root_raw:
        logging.error("EXPORTS_ROOT not set")
        sys.exit(1)

    photos_root = Path(photos_root_raw)
    exports_root = Path(exports_root_raw)

    # DB must work or exit
    try:
        conn = get_connection()
    except Exception as e:
        logging.error(f"DB connection failed: {e}")
        sys.exit(1)


    try:
        web_dir = exports_root / "Web"
        thumb_dir = exports_root / "Thumb"
        metadata_dir = exports_root / "Metadata"
        exts_raw = os.getenv("INGEST_EXTS", "")
        allowed_exts = {e.strip().lower() for e in exts_raw.split(",") if e.strip()}

        # Process files
        pbar = tqdm(iter_files_recursive(photos_root), desc="Scanning", unit="file")
        for path in pbar:
            total += 1
            try:
                if allowed_exts and path.suffix.lower() not in allowed_exts:
                    # keep bar updated even when skipping non-target extensions
                    pbar.set_postfix(
                        scanned=total,
                        inserted=inserted,
                        dup=skipped_duplicate,
                        match=skipped_path_match,
                        changed=changed,
                        failed=failed,
                    )
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

            # show live status + current file
            pbar.set_postfix(
                scanned=total,
                inserted=inserted,
                dup=skipped_duplicate,
                match=skipped_path_match,
                changed=changed,
                failed=failed,
            )
            pbar.set_postfix_str(path.name[:50])

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









