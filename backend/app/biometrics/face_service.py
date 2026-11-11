import base64
import io
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from ..config import settings

def decode_image_input(image_input: str | bytes | Path) -> np.ndarray:
    """
    Decodes an image input which can be:
    - Path object or path string
    - Raw image bytes
    - Base64 data URI string ("data:image/jpeg;base64,...") or raw base64 string
    """
    if isinstance(image_input, (str, Path)) and Path(str(image_input)).exists():
        img = cv2.imread(str(image_input))
        if img is None:
            raise ValueError(f"Could not read image from path: {image_input}")
        return img
        
    if isinstance(image_input, str):
        if "," in image_input:
            image_input = image_input.split(",", 1)[1]
        raw_bytes = base64.b64decode(image_input)
    elif isinstance(image_input, bytes):
        raw_bytes = image_input
    else:
        raise ValueError("Unsupported image input type")
        
    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img

def save_image_array(img: np.ndarray, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)

def compute_face_similarity(ref_img_input: str | bytes | Path, live_img_input: str | bytes | Path) -> dict:
    """
    Compare reference face against submitted/live face.
    Returns:
    {
        "passed": bool,
        "score": float (0.0 to 1.0),
        "threshold": float,
        "failure_reason": str or None
    }
    """
    try:
        img1 = decode_image_input(ref_img_input)
        img2 = decode_image_input(live_img_input)
    except Exception as e:
        return {
            "passed": False,
            "score": 0.0,
            "threshold": settings.FACE_MATCH_THRESHOLD,
            "failure_reason": f"IMAGE_DECODE_ERROR: {str(e)}"
        }
        
    # Resize to standardized dimensions
    target_size = (250, 250)
    i1 = cv2.resize(img1, target_size)
    i2 = cv2.resize(img2, target_size)
    
    # 1. 3D Color Histogram correlation
    h1 = cv2.calcHist([i1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    h2 = cv2.calcHist([i2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(h1, h1)
    cv2.normalize(h2, h2)
    hist_score = max(0.0, float(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)))
    
    # 2. Grayscale L1 normalized similarity
    g1 = cv2.cvtColor(i1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(i2, cv2.COLOR_BGR2GRAY)
    g1_eq = cv2.equalizeHist(g1)
    g2_eq = cv2.equalizeHist(g2)
    diff = np.mean(np.abs(g1_eq.astype(float) - g2_eq.astype(float))) / 255.0
    l1_score = max(0.0, 1.0 - diff)
    
    # 3. ORB keypoint descriptor matching
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(g1_eq, None)
    kp2, des2 = orb.detectAndCompute(g2_eq, None)
    
    orb_score = 0.5
    if des1 is not None and des2 is not None and len(des1) > 0 and len(des2) > 0:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        if matches:
            good_matches = [m for m in matches if m.distance < 60]
            orb_score = min(1.0, len(good_matches) / max(1, min(len(des1), len(des2))))
            
    # Weighted composite score
    composite_score = round(float((hist_score * 0.40) + (l1_score * 0.35) + (orb_score * 0.25)), 5)
    
    threshold = settings.FACE_MATCH_THRESHOLD
    passed = composite_score >= threshold
    failure_reason = None if passed else "SIMILARITY_BELOW_THRESHOLD"
    
    return {
        "passed": passed,
        "score": composite_score,
        "threshold": threshold,
        "failure_reason": failure_reason
    }
