from PIL import Image, ImageCms
import io, os

def export_web_jpg(input_path, output_path, max_size=2560, quality=85):
    img = Image.open(input_path)

    # Convert to sRGB
    icc = img.info.get("icc_profile")
    if icc:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        img = ImageCms.profileToProfile(img, src, dst, outputMode="RGB")
    else:
        img = img.convert("RGB")

    # Resize
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # output file
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_file = os.path.join(output_path, base + ".jpg")

    # Save img
    img.save(
        out_file,
        "JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling=1
    )


def export_thumb_jpg(input_path, output_path, max_size=400, quality=75):
    img = Image.open(input_path)

    # Convert to sRGB
    icc = img.info.get("icc_profile")
    if icc:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        img = ImageCms.profileToProfile(img, src, dst, outputMode="RGB")
    else:
        img = img.convert("RGB")

    # Resize
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # output file
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_file = os.path.join(output_path, base + ".jpg")

    # Save thumbnail
    img.save(
        out_file,
        "JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling=2,
    )