#!/usr/bin/env python3
"""
QR Local Decoder (OpenCV + ZXing-C++ with rich debug)

- Офлайн-декодирование QR/штрихкодов.
- Сначала пробует OpenCV (если установлен), затем ZXing-C++ (pip-only, без brew).
- Работает с PNG/JPG/WEBP и первой страницей PDF (через Pillow).
- Опционально копирует результат в буфер (--copy).
- Режим вебкамеры (--webcam) через OpenCV.

Установка зависимостей:
  pip install opencv-python pillow pyperclip zxing-cpp

Примеры:
  python qr-local-decoder.py file.png
  python qr-local-decoder.py file.png --copy
  python qr-local-decoder.py file.png --debug
"""

import argparse
import sys
import os
import re
from typing import List, Tuple

# --- Optional deps ---
try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except Exception:
    PYPERCLIP_AVAILABLE = False

try:
    import zxingcpp
    ZXING_AVAILABLE = True
except Exception:
    ZXING_AVAILABLE = False

URL_REGEX = re.compile(
    r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,})(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+)',
    re.UNICODE
)

DEBUG_MODE = False
def dbg(msg: str):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)

def is_url(text: str) -> bool:
    return bool(URL_REGEX.search(text or ""))

# -------------------- Loading helpers --------------------
def load_image_cv2(path: str):
    """Load image as OpenCV BGR ndarray. If OpenCV imread fails, try Pillow->ndarray."""
    if CV2_AVAILABLE:
        dbg(f"OpenCV imread: {path}")
        img = cv2.imread(path)
        if img is not None:
            dbg(f"OpenCV image shape: {img.shape}")
            return img
    if PIL_AVAILABLE:
        dbg("Fallback: Pillow -> numpy -> (BGR if cv2 available)")
        try:
            import numpy as np
            with Image.open(path) as im:
                im = im.convert("RGB")
                arr = np.array(im)
                if CV2_AVAILABLE:
                    arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                dbg(f"Pillow-loaded array shape: {arr.shape}")
                return arr
        except Exception as e:
            dbg(f"Pillow fallback failed: {e}")
            return None
    return None

def load_image_pil(path: str):
    if not PIL_AVAILABLE:
        return None
    try:
        im = Image.open(path)
        dbg(f"Pillow loaded image: size={getattr(im, 'size', '?')} mode={getattr(im, 'mode', '?')}")
        return im
    except Exception as e:
        dbg(f"Pillow open failed: {e}")
        return None

# -------------------- Decoders --------------------
def try_decode_opencv(img) -> List[str]:
    """Use OpenCV QRCodeDetector. Logs raw results including empty strings."""
    if not CV2_AVAILABLE or img is None:
        dbg("OpenCV not available or image is None")
        return []
    texts_raw: List[str] = []
    det = cv2.QRCodeDetector()

    # Multi first
    try:
        retval, decoded_info, points, _ = det.detectAndDecodeMulti(img)
        dbg(f"OpenCV detectAndDecodeMulti retval={retval}; decoded_info={repr(decoded_info) if retval else '[]'}")
        if retval and decoded_info:
            texts_raw.extend(decoded_info)
    except Exception as e:
        dbg(f"OpenCV multi decode error: {e}")

    # Single fallback (some builds are better at single)
    if not texts_raw:
        try:
            t, pts, _ = det.detectAndDecode(img)
            dbg(f"OpenCV detectAndDecode single => {repr(t)}")
            if t is not None:
                texts_raw.append(t)
        except Exception as e:
            dbg(f"OpenCV single decode error: {e}")

    # Log all raw (even empties) then filter empties and dedup
    if DEBUG_MODE:
        for i, t in enumerate(texts_raw):
            print(f"[DEBUG] OpenCV raw[{i}] = {repr(t)}")
    seen = set()
    out = []
    for t in texts_raw:
        if t and (t not in seen):
            seen.add(t)
            out.append(t)
    dbg(f"OpenCV unique non-empty: {out}")
    return out

def try_decode_zxing(pil_img) -> List[str]:
    """Use zxingcpp.read_barcodes(PIL.Image). Returns unique texts."""
    if not (ZXING_AVAILABLE and pil_img):
        dbg("ZXing unavailable or no PIL image")
        return []
    try:
        results = zxingcpp.read_barcodes(pil_img)
        dbg(f"ZXing results count: {len(results)}")
        out = []
        seen = set()
        for idx, r in enumerate(results):
            # r.format, r.text, r.bytes, r.position (list of points)
            dbg(f"ZXing[{idx}] type={getattr(r, 'format', '?')} text={repr(getattr(r, 'text', None))} pos={getattr(r, 'position', None)}")
            s = getattr(r, "text", None)
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        dbg(f"ZXing unique: {out}")
        return out
    except Exception as e:
        dbg(f"ZXing failed: {e}")
        return []

# -------------------- High-level decode --------------------
def decode_from_image_path(path: str) -> List[str]:
    dbg(f"Decoding file: {path}")
    # Try OpenCV first
    img_cv = load_image_cv2(path)
    texts = try_decode_opencv(img_cv)
    if texts:
        dbg("OpenCV succeeded with non-empty results")
        return texts

    # ZXing fallback (needs PIL)
    pil_img = load_image_pil(path)
    texts = try_decode_zxing(pil_img)
    if texts:
        dbg("ZXing succeeded with non-empty results")
    else:
        dbg("ZXing also found nothing (or empty)")
    return texts

# -------------------- Webcam --------------------
def decode_from_webcam(copy: bool = False) -> int:
    if not CV2_AVAILABLE:
        print("Error: OpenCV required for webcam mode.", file=sys.stderr)
        return 2

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: cannot access webcam.", file=sys.stderr)
        return 3

    det = cv2.QRCodeDetector()
    seen = set()
    print("Webcam mode: press Q or ESC to quit.")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        got_any = False
        try:
            retval, decoded_info, points, _ = det.detectAndDecodeMulti(frame)
            if retval:
                for t in decoded_info or []:
                    if t and t not in seen:
                        seen.add(t)
                        print(t)
                        if copy and PYPERCLIP_AVAILABLE:
                            pyperclip.copy(t)
                        got_any = True
        except Exception:
            try:
                t, pts, _ = det.detectAndDecode(frame)
                if t and t not in seen:
                    seen.add(t)
                    print(t)
                    if copy and PYPERCLIP_AVAILABLE:
                        pyperclip.copy(t)
                    got_any = True
            except Exception:
                pass

        if got_any:
            cv2.putText(frame, "QR detected!", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imshow("QR Decoder", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0

# -------------------- CLI --------------------
def main(argv: List[str]) -> int:
    global DEBUG_MODE
    p = argparse.ArgumentParser(description="Decode QR codes offline from images or webcam.")
    p.add_argument("paths", nargs="*", help="Image files (PNG/JPG/WEBP/PDF first page)")
    p.add_argument("--webcam", action="store_true", help="Use webcam (OpenCV only)")
    p.add_argument("--copy", action="store_true", help="Copy result to clipboard")
    p.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    args = p.parse_args(argv)

    DEBUG_MODE = args.debug

    if not args.paths and not args.webcam:
        p.print_help()
        return 1

    if args.webcam:
        return decode_from_webcam(copy=args.copy)

    all_results: List[Tuple[str, List[str]]] = []
    for path in args.paths:
        if not os.path.exists(path):
            print(f"{path}: not found", file=sys.stderr)
            continue
        texts = decode_from_image_path(path)
        all_results.append((path, texts))

    exit_code = 0
    for path, texts in all_results:
        if not texts:
            print(f"{path}: no QR found")
            exit_code = max(exit_code, 4)
            continue

        # URLs наперёд
        urls = [t for t in texts if is_url(t)]
        rest = [t for t in texts if t not in urls]
        ordered = urls + rest

        if len(all_results) > 1:
            print(f"--- {path} ---")
        for t in ordered:
            print(t)

        if args.copy and PYPERCLIP_AVAILABLE:
            try:
                pyperclip.copy(ordered[0])
            except Exception:
                warn("Failed to copy to clipboard")

    return exit_code

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
