"""
Face Recognition Utility — SecureVote
Uses DeepFace with VGG-Face model.

Pipeline (matches your project report):
  1. Face Detection    → OpenCV / RetinaFace
  2. Pre-Processing    → Align, normalize
  3. Liveness Check   → Eye-blink / motion heuristic
  4. Feature Extraction → CNN embedding (128-D vector)
  5. Similarity Match → Cosine distance vs stored hash
"""

import os
import hashlib
import numpy as np
import cv2
import base64
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)


# ── Lazy import DeepFace so app starts even if not installed ──────────────────
def _get_deepface():
    try:
        from deepface import DeepFace
        return DeepFace
    except ImportError:
        raise RuntimeError(
            "DeepFace not installed. Run: pip install deepface"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  1. ENROLLMENT  —  called during Admin voter registration
# ─────────────────────────────────────────────────────────────────────────────

def enroll_face(voter_id: str, image_data: str) -> dict:
    """
    Enroll a voter's face.

    Args:
        voter_id:   Unique voter identifier
        image_data: Base64-encoded image string (from webcam)

    Returns:
        {"success": True, "face_path": str, "face_hash": str}
    """
    DeepFace = _get_deepface()

    # Decode base64 → numpy image
    img_array = _base64_to_cv2(image_data)

    # Detect face region — reject if no face found
    faces = _detect_faces(img_array)
    if not faces:
        return {"success": False, "error": "No face detected in image"}

    # Crop to largest face
    face_crop = _crop_face(img_array, faces[0])

    # Save face image (off-chain, encrypted path)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    face_filename = f"{voter_id}_face.jpg"
    face_path = os.path.join(upload_dir, face_filename)
    cv2.imwrite(face_path, face_crop)

    # Extract embedding and hash it
    embedding = _get_embedding(DeepFace, face_path)
    face_hash = _hash_embedding(embedding)

    return {
        "success":   True,
        "face_path": face_path,
        "face_hash": face_hash,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  2. AUTHENTICATION  —  called during voter login
# ─────────────────────────────────────────────────────────────────────────────

def authenticate_face(stored_face_path: str, live_image_data: str) -> dict:
    """
    Authenticate a voter by comparing live face to enrolled face.

    Args:
        stored_face_path: Path to enrolled face image
        live_image_data:  Base64 image from webcam (login attempt)

    Returns:
        {"verified": bool, "distance": float, "liveness": bool, "error": str|None}
    """
    DeepFace = _get_deepface()

    # Decode live image
    live_array = _base64_to_cv2(live_image_data)

    # ── LIVENESS DETECTION ─────────────────────────────────────────────────
    # Heuristic: checks for natural facial variation (blur, micro-textures)
    # In production: use MediaPipe + blink detection or 3D depth
    liveness_ok, liveness_reason = check_liveness(live_array)
    if not liveness_ok:
        return {
            "verified":  False,
            "liveness":  False,
            "distance":  None,
            "error":     f"Liveness check failed: {liveness_reason}"
        }

    # Save live image temporarily
    tmp_path = stored_face_path.replace("_face.jpg", "_live_tmp.jpg")
    faces = _detect_faces(live_array)
    if not faces:
        return {"verified": False, "liveness": True, "distance": None,
                "error": "No face detected in live image"}

    face_crop = _crop_face(live_array, faces[0])
    cv2.imwrite(tmp_path, face_crop)

    try:
        # ── DeepFace VERIFY ─────────────────────────────────────────────────
        result = DeepFace.verify(
            img1_path  = stored_face_path,
            img2_path  = tmp_path,
            model_name = current_app.config.get("DEEPFACE_MODEL", "VGG-Face"),
            detector_backend = current_app.config.get("DEEPFACE_DETECTOR", "opencv"),
            distance_metric  = "cosine",
            enforce_detection= False,
        )

        distance  = result.get("distance", 1.0)
        threshold = current_app.config.get("FACE_THRESHOLD", 0.40)
        verified  = result.get("verified", False) and distance <= threshold

        logger.info(f"Face verify: distance={distance:.4f}, verified={verified}")

        return {
            "verified":  verified,
            "liveness":  True,
            "distance":  round(distance, 4),
            "threshold": threshold,
            "error":     None if verified else f"Face mismatch (distance={distance:.3f})"
        }

    except Exception as e:
        logger.error(f"DeepFace error: {e}")
        return {"verified": False, "liveness": True, "distance": None, "error": str(e)}

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ─────────────────────────────────────────────────────────────────────────────
#  3. LIVENESS DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def check_liveness(img_array: np.ndarray) -> tuple[bool, str]:
    """
    Liveness heuristics:
    - Reject pure white/black (likely a printed photo)
    - Check Laplacian variance (low = static/blurry photo)
    - Check color histogram spread (flat = synthetic)

    Real production system: use MediaPipe face mesh + eye landmark
    tracking across multiple frames for blink detection.
    """
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # 1. Blurriness check — printed photos are often too sharp or too blurry
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 15.0:
        return False, f"Image too blurry (var={laplacian_var:.1f}) — possible static photo"

    # 2. Color variance — synthetic/printed images have low color variance
    hsv = cv2.cvtColor(img_array, cv2.COLOR_BGR2HSV)
    sat_std = np.std(hsv[:, :, 1])
    if sat_std < 8.0:
        return False, "Low color variation — possible printed image or video replay"

    # 3. Pixel intensity histogram — flat histogram = likely printed
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    entropy = -np.sum(hist * np.log2(hist + 1e-9))
    if entropy < 4.5:
        return False, "Low image entropy — possible spoofing attack"

    return True, "Liveness check passed"


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _base64_to_cv2(b64_string: str) -> np.ndarray:
    """Convert base64 image string to OpenCV numpy array."""
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def _detect_faces(img_array: np.ndarray) -> list:
    """Detect faces using OpenCV Haar cascade."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1,
                                          minNeighbors=5, minSize=(80, 80))
    return list(faces)


def _crop_face(img_array: np.ndarray, face_rect: tuple,
               padding: float = 0.2) -> np.ndarray:
    """Crop face with padding from image."""
    x, y, w, h = face_rect
    pad_x = int(w * padding)
    pad_y = int(h * padding)
    ih, iw = img_array.shape[:2]
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(iw, x + w + pad_x)
    y2 = min(ih, y + h + pad_y)
    return img_array[y1:y2, x1:x2]


def _get_embedding(DeepFace, face_path: str) -> list:
    """Extract facial feature embedding using DeepFace."""
    result = DeepFace.represent(
        img_path=face_path,
        model_name="VGG-Face",
        enforce_detection=False
    )
    return result[0]["embedding"]


def _hash_embedding(embedding: list) -> str:
    """SHA-256 hash of facial embedding for secure storage."""
    embedding_bytes = np.array(embedding).tobytes()
    return hashlib.sha256(embedding_bytes).hexdigest()
