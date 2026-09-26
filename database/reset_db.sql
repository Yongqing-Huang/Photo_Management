USE photo_db_test;
DROP DATABASE IF EXISTS photo_db_test;
CREATE DATABASE photo_db_test;
USE photo_db_test;


CREATE TABLE photos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    original_path VARCHAR(768) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    original_sha256 CHAR(64) NOT NULL,

    mime_type VARCHAR(64),
    file_size BIGINT UNSIGNED,

    width INT UNSIGNED,
    height INT UNSIGNED,

    datetime_original DATETIME,
    file_modified_at DATETIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uniq_sha256 (original_sha256),
    UNIQUE KEY uniq_original_path (original_path)
);


CREATE TABLE camera_metadata (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL UNIQUE,

    camera_make VARCHAR(64),
    camera_model VARCHAR(64),
    lens VARCHAR(128),

    iso INT UNSIGNED,
    exposure_time VARCHAR(32),
    fnumber FLOAT,
    focal_length FLOAT,
    focal_length_35mm FLOAT,

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);


CREATE TABLE photo_text_metadata (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL UNIQUE,

    title TEXT,
    caption TEXT,
    alt_text TEXT,
    extended_description TEXT,

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);


CREATE TABLE photo_ratings (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL,

    rating TINYINT UNSIGNED,
    creator_tool VARCHAR(128),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE,

    CHECK (rating BETWEEN 0 AND 5)
);


CREATE TABLE photo_locations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL UNIQUE,

    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),

    city VARCHAR(64),
    state VARCHAR(64),
    country VARCHAR(64),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);


CREATE TABLE photo_variants (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL,

    variant_type VARCHAR(32) NOT NULL,
    path VARCHAR(2048) NOT NULL,

    sha256 CHAR(64),

    width INT UNSIGNED,
    height INT UNSIGNED,

    creator_tool VARCHAR(128),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uniq_variant (photo_id, variant_type),

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);


CREATE TABLE ai_analyses (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT UNSIGNED NOT NULL,

    analysis_type VARCHAR(64) NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (photo_id)
        REFERENCES photos(id)
        ON DELETE CASCADE
);


CREATE TABLE ai_classifications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    analysis_id BIGINT UNSIGNED NOT NULL,

    category VARCHAR(64) NOT NULL,
    label VARCHAR(128) NOT NULL,
    confidence FLOAT NOT NULL,

    FOREIGN KEY (analysis_id)
        REFERENCES ai_analyses(id)
        ON DELETE CASCADE,

    INDEX idx_category_label (category, label),
    INDEX idx_confidence (confidence),

    CHECK (confidence >= 0 AND confidence <= 1)
);