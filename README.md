# Photo Management

## Table of Contents
- [Requirements](#requirements)
  - [.env](#env)
  - [config.py](#configpy)
- [Database](#database)


## Requirements
### `.env`
```env
DB_HOST=localhost
DB_USER=<your_username>
DB_PASSWORD=<password>
DB_NAME=<database>
```

### `config.py`
``` config
DB_CONFIG = {
    "host": "localhost",
    "user": "<user>",
    "password": "<password>",
    "database": "<database>"
}
```

## Database

### photos
- `id` — primary key
- `original_path` — path to original photo
- `original_sha256` — SHA-256 hash (unique)
- `datetime_original` — original capture time
- `created_at` — record creation timestamp

---

### camera_metadata
- `id` — primary key
- `photo_id` — reference to `photos.id`
- `camera_make`
- `camera_model`
- `lens`
- `iso`
- `exposure_time`
- `fnumber`
- `focal_length`

---

### photo_text_metadata
- `id` — primary key
- `photo_id` — reference to `photos.id`
- `title`
- `caption`
- `alt_text`
- `extended_description`

---

### photo_ratings
- `id` — primary key
- `photo_id` — reference to `photos.id`
- `rating`
- `creator_tool`

---

### photo_locations
- `id` — primary key
- `photo_id` — reference to `photos.id`
- `city`
- `state`
- `country`

---

### photo_variants
- `id` — primary key
- `photo_id` — reference to `photos.id`
- `variant` — `web` or `thumb`
- `path` — file path
- `width`
- `height`
- `created_at`