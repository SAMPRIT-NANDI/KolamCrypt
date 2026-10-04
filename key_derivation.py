import os
import hashlib
from pathlib import Path
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
import config

def hash_kolam_image(kolam_image_path: str) -> bytes:
    """Read Kolam image file bytes and return SHA-256 hash digest."""
    path = Path(kolam_image_path)
    if not path.exists():
        raise FileNotFoundError(f"Kolam pattern image not found at: {kolam_image_path}")
    
    with open(path, "rb") as f:
        image_bytes = f.read()
        
    return hashlib.sha256(image_bytes).digest()

def hash_kolam_bytes(image_bytes: bytes) -> bytes:
    """Compute SHA-256 hash digest directly from raw Kolam image bytes."""
    return hashlib.sha256(image_bytes).digest()

def derive_key(password: str, kolam_image_path: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Derive a 256-bit AES encryption key using password + Kolam pattern image hash.
    
    Args:
        password: User secret password string
        kolam_image_path: Path to generated Kolam image file
        salt: Optional 16-byte salt. Generated randomly if None.
        
    Returns:
        (derived_key_bytes, salt_bytes)
    """
    if not password:
        raise ValueError("Password cannot be empty.")
        
    if salt is None:
        salt = os.urandom(config.SALT_SIZE)
        
    # Extract SHA-256 fingerprint of the Kolam image
    kolam_hash = hash_kolam_image(kolam_image_path)
    
    # Secret material = password + Kolam image hash
    secret_material = password.encode('utf-8') + kolam_hash
    
    # Run PBKDF2 key derivation with 100,000 iterations
    derived_key = PBKDF2(
        password=secret_material,
        salt=salt,
        dkLen=config.AES_KEY_SIZE,
        count=config.PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256
    )
    
    return derived_key, salt

def derive_key_from_bytes(password: str, image_bytes: bytes, salt: bytes = None) -> tuple[bytes, bytes]:
    """Derive key directly using in-memory image bytes."""
    if not password:
        raise ValueError("Password cannot be empty.")
    if salt is None:
        salt = os.urandom(config.SALT_SIZE)
        
    kolam_hash = hash_kolam_bytes(image_bytes)
    secret_material = password.encode('utf-8') + kolam_hash
    
    derived_key = PBKDF2(
        password=secret_material,
        salt=salt,
        dkLen=config.AES_KEY_SIZE,
        count=config.PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256
    )
    return derived_key, salt

if __name__ == "__main__":
    from kolam_generator import generate_kolam
    sample_path = generate_kolam("test_seed")
    key, salt = derive_key("my_secure_password_123", sample_path)
    print(f"Derived Key (hex): {key.hex()}")
    print(f"Salt (hex): {salt.hex()}")
