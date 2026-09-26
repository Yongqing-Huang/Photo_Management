import mysql.connector
from src.photo_management.config import DB_CONFIG
import hashlib
import logging
from mysql.connector import Error
from pathlib import Path

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# Helper: get photo id by sha256
def get_photo_id_by_sha256(conn, sha256: str):
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM photos WHERE original_sha256=%s LIMIT 1",
            (sha256,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()


# Helper: get photo id by path
def get_photo_id_by_path(conn, original_path: str):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id
            FROM photos
            WHERE original_path = %s LIMIT 1
            """,
            (original_path,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()


# Helper: get sha256 by path
def get_photo_sha256_by_path(conn, original_path: str):
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT original_sha256 FROM photos WHERE original_path=%s LIMIT 1",
            (original_path,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()


# Helper: get photo path by photo id
def get_photo_path_by_id(conn, photo_id: int):
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT original_path FROM photos WHERE id=%s LIMIT 1",
            (photo_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()

def upsert_photo_variants(conn, photo_id: int, variant_paths: dict):
    cur = conn.cursor()

    try:
        for variant_type, variant_info in variant_paths.items():

            # Allow either:
            # {"web": "/path/file.jpg"}
            # or:
            # {"web": {"path": "...", "width": ..., "height": ...}}

            if isinstance(variant_info, str):
                path = variant_info
                width = None
                height = None
                sha256 = None
                creator_tool = None
            else:
                path = variant_info.get("path")
                width = variant_info.get("width")
                height = variant_info.get("height")
                sha256 = variant_info.get("sha256")
                creator_tool = variant_info.get("creator_tool")

            cur.execute(
                """
                INSERT INTO photo_variants (
                    photo_id,
                    variant_type,
                    path,
                    sha256,
                    width,
                    height,
                    creator_tool
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)

                ON DUPLICATE KEY UPDATE
                    path = VALUES(path),
                    sha256 = VALUES(sha256),
                    width = VALUES(width),
                    height = VALUES(height),
                    creator_tool = VALUES(creator_tool)
                """,
                (
                    photo_id,
                    variant_type,
                    path,
                    sha256,
                    width,
                    height,
                    creator_tool,
                )
            )

    finally:
        cur.close()


def insert_full_metadata(
    conn,
    photo_path: str,
    fields: dict,
    variant_paths: dict | None = None
):
    cur = conn.cursor()

    try:
        # --------------------------------------------------
        # Basic file information
        # --------------------------------------------------
        path = Path(photo_path)

        sha256 = sha256_file(photo_path)
        filename = path.name
        file_size = path.stat().st_size

        # --------------------------------------------------
        # Check duplicate
        # --------------------------------------------------
        existing_id = get_photo_id_by_sha256(conn, sha256)

        if existing_id is not None:
            logging.info(
                f"Skip duplicate: photo_id={existing_id}, "
                f"path={photo_path}"
            )
            return existing_id

        # --------------------------------------------------
        # Photo
        # --------------------------------------------------
        cur.execute(
            """
            INSERT INTO photos (
                original_path,
                original_filename,
                original_sha256,
                mime_type,
                file_size,
                width,
                height,
                datetime_original
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(path),
                filename,
                sha256,
                fields.get("mime_type"),
                file_size,
                fields.get("width"),
                fields.get("height"),
                fields.get("datetime_original"),
            )
        )

        photo_id = cur.lastrowid

        # --------------------------------------------------
        # Camera metadata
        # --------------------------------------------------
        cur.execute(
            """
            INSERT INTO camera_metadata (
                photo_id,
                camera_make,
                camera_model,
                lens,
                iso,
                exposure_time,
                fnumber,
                focal_length
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                photo_id,
                fields.get("make"),
                fields.get("model"),
                fields.get("lens"),
                fields.get("iso"),
                fields.get("exposure_time"),
                fields.get("fnumber"),
                fields.get("focal_length"),
            )
        )

        # --------------------------------------------------
        # Text metadata
        # --------------------------------------------------
        cur.execute(
            """
            INSERT INTO photo_text_metadata (
                photo_id,
                title,
                caption,
                alt_text,
                extended_description
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                photo_id,
                fields.get("title"),
                fields.get("caption"),
                fields.get("alt_text"),
                fields.get("extended_description"),
            )
        )

        # --------------------------------------------------
        # Rating
        # --------------------------------------------------
        rating = fields.get("rating")

        cur.execute(
            """
            INSERT INTO photo_ratings (
                photo_id,
                rating,
                creator_tool
            )
            VALUES (%s, %s, %s)
            """,
            (
                photo_id,
                int(rating) if rating is not None else None,
                fields.get("creator_tool"),
            )
        )

        # --------------------------------------------------
        # Location
        # --------------------------------------------------
        cur.execute(
            """
            INSERT INTO photo_locations (
                photo_id,
                latitude,
                longitude,
                city,
                state,
                country
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                photo_id,
                fields.get("latitude"),
                fields.get("longitude"),
                fields.get("city"),
                fields.get("state"),
                fields.get("country"),
            )
        )

        # --------------------------------------------------
        # Variants
        # --------------------------------------------------
        if variant_paths:
            upsert_photo_variants(
                conn,
                photo_id,
                variant_paths
            )

        # --------------------------------------------------
        # Finish transaction
        # --------------------------------------------------
        conn.commit()

        logging.info(
            f"Inserted photo_id={photo_id}, "
            f"filename={filename}"
        )

        return photo_id

    except Exception:
        conn.rollback()
        logging.exception(
            f"Failed to insert photo: {photo_path}"
        )
        raise

    finally:
        cur.close()


def fetch_all_photos(conn):
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM photos")
    rows = cur.fetchall()

    cur.close()

    return rows



def test_connection():
    try:
        conn = get_connection()
        if conn.is_connected():
            print("MySQL connection successful.")
            print("Server version:", conn.get_server_info())
        conn.close()
    except Error as e:
        print("MySQL connection failed.")
        print("Error:", e)

if __name__ == "__main__":
    print("Testing database connection...")
    test_connection()