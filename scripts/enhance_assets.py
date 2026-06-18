from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "enhanced"
MODEL_FSRCNN = ROOT / "tools" / "models" / "FSRCNN_x4.pb"


PHOTO_ASSETS = [
    ("photos_jpg_3x/03_seasonal_menu_plate.jpg", "seasonal-menu-plate.jpg", 1600, (0, 8, 0, 24)),
    ("photos_jpg_3x/04_chef_portrait.jpg", "chef-portrait.jpg", 1500, (0, 0, 0, 12)),
    ("photos_jpg_3x/05_private_dining_room_wide.jpg", "private-dining-room.jpg", 2200, (0, 0, 0, 18)),
    ("photos_jpg_3x/06_gallery_dining_table.jpg", "gallery-dining-table.jpg", 1000, (0, 0, 0, 0)),
    ("photos_jpg_3x/07_gallery_cocktail.jpg", "gallery-cocktail.jpg", 1000, (0, 0, 0, 0)),
    ("photos_jpg_3x/08_gallery_greenhouse_interior.jpg", "gallery-greenhouse-interior.jpg", 1000, (0, 0, 0, 0)),
    ("photos_jpg_3x/09_gallery_plated_dish.jpg", "gallery-plated-dish.jpg", 1000, (0, 0, 0, 0)),
    ("photos_jpg_3x/10_gallery_lounge.jpg", "gallery-lounge.jpg", 1000, (0, 0, 0, 0)),
]


def imread(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return image


def imwrite(path: Path, image: np.ndarray, quality: int = 90) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if ext in {".jpg", ".jpeg"} else []
    ok, data = cv2.imencode(ext, image, params)
    if not ok:
        raise RuntimeError(f"Could not encode image: {path}")
    data.tofile(str(path))


def crop_dark_border(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = gray > 9
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return image
    top, bottom = rows[0], rows[-1] + 1
    left, right = cols[0], cols[-1] + 1
    return image[top:bottom, left:right]


def local_contrast(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.35, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    return cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)


def color_grade(image: np.ndarray, warmth: float = 1.03, green: float = 1.02) -> np.ndarray:
    graded = image.astype(np.float32)
    graded[..., 2] *= warmth
    graded[..., 1] *= green
    graded[..., 0] *= 0.98
    return np.clip(graded, 0, 255).astype(np.uint8)


def unsharp(image: np.ndarray, amount: float = 0.58, radius: float = 1.0) -> np.ndarray:
    blur = cv2.GaussianBlur(image, (0, 0), radius)
    return cv2.addWeighted(image, 1.0 + amount, blur, -amount, 0)


def resize_to_width(image: np.ndarray, width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w == width:
        return image
    height = round(h * width / w)
    interpolation = cv2.INTER_AREA if width < w else cv2.INTER_LANCZOS4
    return cv2.resize(image, (width, height), interpolation=interpolation)


def superres(image: np.ndarray, max_output_width: int) -> np.ndarray:
    if MODEL_FSRCNN.exists():
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(MODEL_FSRCNN))
        sr.setModel("fsrcnn", 4)
        upscaled = sr.upsample(image)
    else:
        upscaled = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)

    if upscaled.shape[1] > max_output_width:
        upscaled = resize_to_width(upscaled, max_output_width)
    return upscaled


def crop_pixels(image: np.ndarray, crop: tuple[int, int, int, int]) -> np.ndarray:
    left, top, right, bottom = crop
    h, w = image.shape[:2]
    return image[top : h - bottom if bottom else h, left : w - right if right else w]


def enhance_photo(src: Path, dest: Path, target_width: int, crop: tuple[int, int, int, int]) -> None:
    image = imread(src)
    image = crop_dark_border(image)
    image = crop_pixels(image, crop)
    image = superres(image, target_width)
    image = local_contrast(image)
    image = color_grade(image)
    image = unsharp(image)
    imwrite(dest, image, quality=91)


def inpaint_hero() -> None:
    image = imread(ROOT / "photos_jpg_3x" / "01b_hero_background_clean_inpainted.jpg")
    h, w = image.shape[:2]
    artifact_mask = np.zeros((h, w), dtype=np.uint8)
    for x1, y1, x2, y2 in [(1150, 575, 1680, 845), (230, 990, 1040, 1235)]:
        cv2.rectangle(artifact_mask, (x1, y1), (x2, y2), 255, -1)
    image = cv2.inpaint(image, artifact_mask, 9, cv2.INPAINT_TELEA)

    blurred = cv2.GaussianBlur(image, (0, 0), 46)
    blurred = color_grade(blurred, warmth=0.96, green=1.06).astype(np.float32)
    tint = np.full_like(blurred, (14, 30, 12), dtype=np.float32)
    blurred = cv2.addWeighted(blurred, 0.64, tint, 0.36, 0)

    x = np.arange(w, dtype=np.float32)
    mask_x = 1 - np.clip((x - 1480) / 820, 0, 1)
    mask = np.repeat(mask_x[None, :, None], h, axis=0)

    clean = image.astype(np.float32) * (1 - mask) + blurred * mask
    clean = np.clip(clean, 0, 255).astype(np.uint8)
    clean = color_grade(clean, warmth=1.01, green=1.02)
    clean = unsharp(clean, amount=0.28, radius=1.1)
    imwrite(OUT / "hero-clean.jpg", clean, quality=92)


def write_svg_assets() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "olive-mark.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 92 42" fill="none">
  <g stroke="#a79555" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M13 28C32 19 52 16 78 13"/>
    <path d="M29 22C23 10 17 7 8 6c2 9 8 15 21 16Z" fill="#c2b16f"/>
    <path d="M39 18C36 7 31 3 23 1c0 9 5 15 16 17Z" fill="#b8a760"/>
    <path d="M49 16C48 6 43 2 36 0c-1 9 3 15 13 16Z" fill="#ab9b55"/>
    <path d="M55 15C61 6 68 4 76 5c-3 8-10 12-21 10Z" fill="#c2b16f"/>
    <path d="M44 19C50 27 57 31 66 31c-4-8-11-12-22-12Z" fill="#968b4d"/>
    <path d="M31 24C38 32 46 35 55 34c-5-8-13-11-24-10Z" fill="#a99d58"/>
  </g>
</svg>
""",
        encoding="utf-8",
    )
    (OUT / "olive-branch.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 300" fill="none">
  <g stroke="#5b5f3d" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    <path d="M62 208C187 148 331 102 520 72"/>
    <path d="M166 162C127 107 85 82 28 82c16 48 61 77 138 80Z" fill="#90936a"/>
    <path d="M235 138C204 75 162 45 101 40c13 57 61 91 134 98Z" fill="#7e855f"/>
    <path d="M315 116C279 62 237 38 177 36c15 53 62 83 138 80Z" fill="#a1a77b"/>
    <path d="M378 103C404 46 450 23 522 33c-22 51-70 76-144 70Z" fill="#87915f"/>
    <path d="M295 128C338 188 391 215 454 207c-27-55-82-82-159-79Z" fill="#70794f"/>
    <path d="M206 154C249 214 302 241 365 233c-27-55-82-82-159-79Z" fill="#87915f"/>
    <path d="M116 192C160 247 212 270 271 258c-31-51-84-73-155-66Z" fill="#a1a77b"/>
    <circle cx="407" cy="94" r="23" fill="#6f743e"/>
    <circle cx="462" cy="82" r="22" fill="#8b8d4b"/>
    <circle cx="342" cy="119" r="19" fill="#7d8247"/>
  </g>
</svg>
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inpaint_hero()
    for src, dest, width, crop in PHOTO_ASSETS:
        enhance_photo(ROOT / src, OUT / dest, width, crop)
    write_svg_assets()


if __name__ == "__main__":
    main()
