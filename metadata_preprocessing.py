from PIL import Image
from PIL.PngImagePlugin import PngImageFile
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import logging

def get_xmp_str(path: str) -> str:
    img = Image.open(path)
    return str(img.info[('XML:com.adobe.xmp')])


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


def extract_xmp_fields(xmp_str: str) -> dict:
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


# Convert EXIF fraction string to float
def frac_to_float(x):
    if not x:
        return None

    if isinstance(x, str) and "/" in x:
        try:
            a, b = x.split("/")
            return float(a) / float(b)
        except Exception:
            return None

    try:
        return float(x)
    except Exception:
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
def parse_datetime(dt_str):
    if not dt_str:
        return None

    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


# Remove Whitespace and Empty String
def clean_text(x):
    if not x:
        return None

    x = x.strip()
    return x if x else None


def normalize_xmp_fields(fields: dict) -> dict:

    return {
        **fields,

        # Camera numeric
        "iso": parse_iso(fields.get("iso")),
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




if __name__ == "__main__":
    path = "Test/Photos/test.png"
    output_folder = "temp"
    xmp_str = get_xmp_str(path)
    print(extract_xmp_fields(xmp_str))

