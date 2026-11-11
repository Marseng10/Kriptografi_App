import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

MAGIC_HEADER = b"WCPT"

def generate_default_cover_image(output_path: Path, title: str = "WARISCRYPT DIGITAL INHERITANCE"):
    """
    Generate an elegant parchment/vintage style carrier image if no custom image is supplied.
    """
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(26, 32, 44))
    draw = ImageDraw.Draw(img)
    
    # Outer ornamental border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(197, 168, 128), width=3)
    draw.rectangle([(28, 28), (width - 28, height - 28)], outline=(139, 30, 30), width=1)
    
    # Ornamental corner accents
    for x in [30, width - 50]:
        for y in [30, height - 50]:
            draw.rectangle([(x, y), (x + 20, y + 20)], fill=(197, 168, 128))
    
    # Central banner box
    draw.rectangle([(60, 180), (width - 60, 420)], fill=(15, 23, 42), outline=(197, 168, 128), width=2)
    
    # Title & text
    draw.text((width // 2 - 190, 220), "WARISCRYPT", fill=(197, 168, 128))
    draw.text((width // 2 - 220, 270), "SECURE DIGITAL INHERITANCE VAULT", fill=(226, 232, 240))
    draw.text((width // 2 - 250, 320), "Cryptographic Steganography Carrier Image", fill=(148, 163, 184))
    draw.text((width // 2 - 160, 370), "Confidential - For Designated Beneficiary", fill=(139, 30, 30))
    
    img.save(output_path, format="PNG")
    return output_path

def embed_secret_in_image(cover_path: Path, secret_bytes: bytes, output_path: Path) -> Path:
    """
    Embed secret bytes into a PNG image using LSB (Least Significant Bit).
    Payload structure: [4 bytes MAGIC "WCPT"] + [4 bytes length] + [secret_bytes].
    """
    img = Image.open(cover_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    
    payload = MAGIC_HEADER + len(secret_bytes).to_bytes(4, "big") + secret_bytes
    bits = []
    for b in payload:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
            
    total_bits = len(bits)
    flat = arr.flatten()
    if total_bits > len(flat):
        raise ValueError(f"Image capacity exceeded. Image can hold {len(flat) // 8} bytes, payload requires {len(payload)} bytes.")
    
    flat[:total_bits] = (flat[:total_bits] & 0xFE) | np.array(bits, dtype=np.uint8)
    stego_arr = flat.reshape(arr.shape)
    stego_img = Image.fromarray(stego_arr)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stego_img.save(output_path, format="PNG")
    return output_path

def extract_secret_from_image(stego_path: Path) -> bytes:
    """
    Extract embedded secret bytes from a PNG image using LSB.
    Verifies the magic header and payload integrity.
    """
    img = Image.open(stego_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    flat = arr.flatten()
    
    # 1. Check Magic Header (32 bits)
    magic_bits = flat[:32] & 1
    magic_bytes = bytearray()
    for i in range(0, 32, 8):
        val = 0
        for b in magic_bits[i:i+8]:
            val = (val << 1) | int(b)
        magic_bytes.append(val)
        
    if bytes(magic_bytes) != MAGIC_HEADER:
        raise ValueError("Gambar ini tidak memuat token WARISCRYPT yang valid (Magic header tidak cocok).")
        
    # 2. Extract length (32 bits)
    len_bits = flat[32:64] & 1
    length = 0
    for b in len_bits:
        length = (length << 1) | int(b)
        
    total_bits = 64 + length * 8
    if total_bits > len(flat) or length <= 0 or length > 10 * 1024 * 1024:
        raise ValueError("Panjang payload steganografi rusak atau tidak valid.")
        
    # 3. Extract secret data
    data_bits = flat[64:total_bits] & 1
    data_bytes = bytearray()
    for i in range(0, len(data_bits), 8):
        val = 0
        for b in data_bits[i:i+8]:
            val = (val << 1) | int(b)
        data_bytes.append(val)
        
    return bytes(data_bytes)
