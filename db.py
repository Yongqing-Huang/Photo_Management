import mysql.connector
from config import DB_CONFIG
import hashlib
import logging


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


def insert_full_metadata(conn, photo_path: str, fields: dict):
    cur = conn.cursor()

    try:
        # -------------------------
        # 1️⃣ Insert into photos
        # -------------------------
        sha256 = sha256_file(photo_path)
        existing_id = get_photo_id_by_sha256(conn, sha256)
        if existing_id is not None:
            logging.info(f"Skip (duplicate): photo_id={existing_id}")
            return existing_id

        cur.execute(
            """
            INSERT INTO photos (
                original_path,
                original_sha256,
                datetime_original
            )
            VALUES (%s,%s,%s)
            ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
            """,
            (
                photo_path,
                sha256,
                fields.get("datetime_original"),
            )
        )

        photo_id = cur.lastrowid

        # Insert Camera Metadata
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
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
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

        # Insert Photo Metadata
        cur.execute(
            """
            INSERT INTO photo_text_metadata (
                photo_id,
                title,
                caption,
                alt_text,
                extended_description
            )
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                photo_id,
                fields.get("title"),
                fields.get("caption"),
                fields.get("alt_text"),
                fields.get("extended_description"),
            )
        )

        # Insert Rating
        cur.execute(
            """
            INSERT INTO photo_ratings (
                photo_id,
                rating,
                creator_tool
            )
            VALUES (%s,%s,%s)
            """,
            (
                photo_id,
                int(fields["rating"]) if fields.get("rating") else None,
                fields.get("creator_tool"),
            )
        )

        # Insert Location
        cur.execute(
            """
            INSERT INTO photo_locations (
                photo_id,
                city,
                state,
                country
            )
            VALUES (%s,%s,%s,%s)
            """,
            (
                photo_id,
                fields.get("city"),
                fields.get("state"),
                fields.get("country"),
            )
        )

        conn.commit()
        logging.info(f"Inserted photo_id={photo_id}")

    except Exception as e:
        conn.rollback()
        logging.info("Insert failed:", e)

    finally:
        cur.close()


def fetch_all_photos(conn):
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM photos")
    rows = cur.fetchall()

    cur.close()

    return rows