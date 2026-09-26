from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngImageFile
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import logging

def get_xmp_str(path: str) -> str:
    with Image.open(path) as img:
        xmp = img.info.get("XML:com.adobe.xmp")

        if xmp is None:
            return None

        if isinstance(xmp, bytes):
            return xmp.decode("utf-8", errors="replace")

        return str(xmp)


def export_metadata_to_txt(path, output_folder):
    img = Image.open(path)

    # Output file path
    out_dir = output_folder
    os.makedirs(out_dir, exist_ok=True)

    img_name = os.path.basename(path)
    out_path = os.path.join(out_dir, img_name + ".txt")

    with open(out_path, "w", encoding="utf-8") as f:

        f.write("INFO KEYS:\n")
        f.write(str(list(img.info.keys())) + "\n\n")

        f.write("INFO DICT:\n")
        for k, v in img.info.items():
            f.write(f"{k} = {v}\n")

        f.write("\n")

        if isinstance(img, PngImageFile):
            f.write("TEXT KEYS:\n")
            f.write(str(list(img.text.keys())) + "\n\n")

            for k, v in img.text.items():
                f.write(f"{k} = {v}\n")

    logging.info(f"Saved metadata to: {out_path}")


def extract_exif_fields(path: str):
    with Image.open(path) as img:
        fields = {
            "mime_type": Image.MIME.get(img.format),
            "width": img.width,
            "height": img.height,
        }

        exif = img.getexif()

        if not exif:
            return fields

        # Main EXIF / IFD0
        exif_data = {
            ExifTags.TAGS.get(tag_id, tag_id): value
            for tag_id, value in exif.items()
        }

        fields.update({
            "make": exif_data.get("Make"),
            "model": exif_data.get("Model"),
        })

        # EXIF sub-IFD
        try:
            exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)

            exif_sub_data = {
                ExifTags.TAGS.get(tag_id, tag_id): value
                for tag_id, value in exif_ifd.items()
            }

            fields.update({
                "iso": (
                    exif_sub_data.get("ISOSpeedRatings")
                    or exif_sub_data.get("PhotographicSensitivity")
                ),
                "exposure_time": exif_sub_data.get("ExposureTime"),
                "fnumber": exif_sub_data.get("FNumber"),
                "focal_length": exif_sub_data.get("FocalLength"),
                "datetime_original": exif_sub_data.get("DateTimeOriginal"),
            })

        except (KeyError, AttributeError):
            pass

        # Fallback dates
        if not fields.get("datetime_original"):
            fields["datetime_original"] = (
                exif_data.get("DateTimeOriginal")
                or exif_data.get("DateTime")
            )

        return fields


def extract_xmp_fields(xmp_str: str):
    if not xmp_str:
        return {}

    start = xmp_str.find("<x:xmpmeta")
    if start != -1:
        xmp_str = xmp_str[start:]

    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "exif": "http://ns.adobe.com/exif/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "photoshop": "http://ns.adobe.com/photoshop/1.0/",
        "Iptc4xmpCore": "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/",
    }

    root = ET.fromstring(xmp_str)
    desc = root.find(".//rdf:Description", ns)
    if desc is None:
        return {}

    a = desc.attrib

    def get_attr(ns_uri, tag):
        return a.get(f"{{{ns_uri}}}{tag}")

    def get_seq_first(prefix, tag):
        li = desc.find(f"./{prefix}:{tag}/rdf:Seq/rdf:li", ns)
        return li.text.strip() if (li is not None and li.text) else None

    def get_alt_text(prefix, tag, lang="x-default"):
        alt = desc.find(f"./{prefix}:{tag}/rdf:Alt", ns)
        if alt is None:
            return None
        # xml:lang is stored under the XML namespace in ElementTree
        xml_lang_key = "{http://www.w3.org/XML/1998/namespace}lang"
        for li in alt.findall("./rdf:li", ns):
            if li is not None and (li.get(xml_lang_key) == lang or (lang is None)):
                if li.text:
                    return li.text.strip()
        # fallback: return first li if present
        li0 = alt.find("./rdf:li", ns)
        return li0.text.strip() if (li0 is not None and li0.text) else None


    return {
        "title": get_alt_text("dc", "title"),
        "caption": get_alt_text("dc", "description"),
        "alt_text": get_alt_text("Iptc4xmpCore", "AltTextAccessibility"),
        "extended_description": get_alt_text("Iptc4xmpCore", "ExtDescrAccessibility"),
        "rating": get_attr("http://ns.adobe.com/xap/1.0/", "Rating"),
        "creator_tool": get_attr("http://ns.adobe.com/xap/1.0/", "CreatorTool"),
        "make": get_attr("http://ns.adobe.com/tiff/1.0/", "Make"),
        "model": get_attr("http://ns.adobe.com/tiff/1.0/", "Model"),
        "lens": get_attr("http://ns.adobe.com/exif/1.0/aux/", "Lens"),
        "iso": get_seq_first("exif", "ISOSpeedRatings"),
        "exposure_time": get_attr("http://ns.adobe.com/exif/1.0/", "ExposureTime"),
        "fnumber": get_attr("http://ns.adobe.com/exif/1.0/", "FNumber"),
        "focal_length": get_attr("http://ns.adobe.com/exif/1.0/", "FocalLength"),
        "datetime_original": get_attr("http://ns.adobe.com/exif/1.0/", "DateTimeOriginal"),
        "lr_exposure2012": get_attr("http://ns.adobe.com/camera-raw-settings/1.0/", "Exposure2012"),
        "state": get_attr("http://ns.adobe.com/photoshop/1.0/", "State"),
        "city": get_attr("http://ns.adobe.com/photoshop/1.0/", "City"),
        "country": get_attr("http://ns.adobe.com/photoshop/1.0/", "Country"),

    }


def merge_metadata(exif_fields: dict, xmp_fields: dict) -> dict:
    merged = exif_fields.copy()

    for key, value in xmp_fields.items():
        if value is not None:
            merged[key] = value

    return merged


# Convert EXIF fraction string to float
def frac_to_float(x):
    if x is None:
        return None

    try:
        if isinstance(x, str):
            x = x.strip()

            if "/" in x:
                numerator, denominator = x.split("/", 1)
                return float(numerator) / float(denominator)

        return float(x)

    except (TypeError, ValueError, ZeroDivisionError):
        return None


# Convert ISO string to int
def parse_iso(x):
    if not x:
        return None

    try:
        return int(x)
    except Exception:
        return None


# Convert ISO datetime to MySQL DATETIME string
def parse_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    value = str(value).strip()

    # XMP
    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # Standard EXIF
    try:
        dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    return None


def exposure_to_string(x):
    if x is None:
        return None

    # XMP files has proper exposure time
    if isinstance(x, str):
        x = x.strip()

        if "/" in x:
            try:
                numerator, denominator = x.split("/", 1)
                numerator = int(numerator)
                denominator = int(denominator)

                if denominator != 0:
                    return f"{numerator}/{denominator}"
            except (ValueError, ZeroDivisionError):
                pass

    try:
        seconds = float(x)
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    if seconds <= 0:
        return None

    # Exposure shorter than 1 second
    if seconds < 1:
        denominator = round(1 / seconds)
        return f"1/{denominator}"

    # Whole-second exposure
    if seconds.is_integer():
        return str(int(seconds))

    # Longer fractional exposures
    return f"{seconds:.1f}"



# Remove Whitespace and Empty String
def clean_text(x):
    if not x:
        return None

    x = x.strip()
    return x if x else None




def normalize_metadata(fields: dict) -> dict:

    return {
        **fields,

        # Camera numeric
        "iso": parse_iso(fields.get("iso")),
        "exposure_time": exposure_to_string(fields.get("exposure_time")),
        "fnumber": frac_to_float(fields.get("fnumber")),
        "focal_length": frac_to_float(fields.get("focal_length")),

        # Datetime
        "datetime_original": parse_datetime(
            fields.get("datetime_original")
        ),

        # Text metadata
        "title": clean_text(fields.get("title")),
        "caption": clean_text(fields.get("caption")),
        "alt_text": clean_text(fields.get("alt_text")),
        "extended_description": clean_text(
            fields.get("extended_description")
        ),

        # Location
        "city": clean_text(fields.get("city")),
        "state": clean_text(fields.get("state")),
        "country": clean_text(fields.get("country")),
    }


def extract_metadata(path: str) -> dict:
    # EXIF
    exif_fields = extract_exif_fields(path)

    # XMP
    xmp_str = get_xmp_str(path)
    xmp_fields = extract_xmp_fields(xmp_str)

    # Combine
    fields = merge_metadata(
        exif_fields,
        xmp_fields
    )

    # Normalize for database
    return normalize_metadata(fields)


if __name__ == "__main__":
    path = "../../Test/Photos/test/test.png"
    output_folder = "temp"
    xmp_str = get_xmp_str(path)
    print(extract_xmp_fields(xmp_str))

