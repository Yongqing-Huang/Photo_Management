DROP DATABASE IF EXISTS  photo_db_test;
CREATE DATABASE photo_db_test;
USE photo_db_test;


CREATE TABLE IF NOT EXISTS photos(
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    original_path VARCHAR(768) NOT NULL,
    original_sha256 CHAR(64) NOT NULL,

    datetime_original DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uniq_sha256 (original_sha256),
    UNIQUE KEY uniq_origional_pah(original_path)
);

CREATE TABLE IF NOT EXISTS camera_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,

    camera_make VARCHAR(64),
    camera_model VARCHAR(64),
    lens VARCHAR(128),

    iso INT,
    exposure_time VARCHAR(32),
    fnumber FLOAT,
    focal_length FLOAT,

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS photo_text_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,

    title TEXT,
    caption TEXT,
    alt_text TEXT,
    extended_description TEXT,

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS photo_ratings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,

    rating TINYINT,
    creator_tool VARCHAR(128),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS photo_locations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,

    city VARCHAR(64),
    state VARCHAR(64),
    country VARCHAR(64),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS photo_variants (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,

    variant ENUM('web','thumb') NOT NULL,
    path VARCHAR(2048) NOT NULL,

    width INT,
    height INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uniq_variant (photo_id, variant),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);