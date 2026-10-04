import os
from pathlib import Path
from Crypto.Cipher import AES
import config

MAGIC_HEADER = b"KCRYPT" # 6 bytes header identifier

def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """
    Encrypt raw bytes using AES-256-GCM.
    
    Structure of output payload:
    [MAGIC_HEADER (6 bytes)] + [NONCE (12 bytes)] + [TAG (16 bytes)] + [CIPHERTEXT]
    """
    if len(key) != config.AES_KEY_SIZE:
        raise ValueError(f"Key must be {config.AES_KEY_SIZE} bytes (256 bits). Received {len(key)} bytes.")
        
    # Generate explicit 12-byte Nonce for NIST compliant AES-GCM
    nonce = os.urandom(config.AES_IV_SIZE if config.AES_IV_SIZE == 12 else 12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    
    # Pack payload: 6 + 12 + 16 = 34 bytes header total
    return MAGIC_HEADER + nonce + tag + ciphertext

def decrypt_bytes(encrypted_payload: bytes, key: bytes) -> bytes:
    """
    Decrypt raw bytes using AES-256-GCM.
    Validates payload structure and authentication tag.
    """
    if len(key) != config.AES_KEY_SIZE:
        raise ValueError(f"Key must be {config.AES_KEY_SIZE} bytes (256 bits). Received {len(key)} bytes.")
        
    header_len = len(MAGIC_HEADER)
    if len(encrypted_payload) < header_len + 12 + 16:
        raise ValueError("Invalid encrypted payload: Payload is too short.")
        
    # Header check
    header = encrypted_payload[:header_len]
    if header != MAGIC_HEADER:
        raise ValueError("Invalid format: Missing KCrypt magic header.")
        
    nonce = encrypted_payload[header_len:header_len + 12]
    tag = encrypted_payload[header_len + 12:header_len + 28]
    ciphertext = encrypted_payload[header_len + 28:]
    
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
        return decrypted_data
    except ValueError as e:
        raise ValueError("Decryption failed: Incorrect password or tampered ciphertext.") from e

def encrypt_file(file_path: str, key: bytes, output_path: str = None) -> str:
    """
    Encrypt a file using AES-256-GCM and write to output path.
    Returns path to the encrypted file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
        
    with open(path, "rb") as f:
        file_data = f.read()
        
    encrypted_payload = encrypt_bytes(file_data, key)
    
    if output_path is None:
        output_path = str(path.parent / f"{path.name}.kcrypt")
        
    with open(output_path, "wb") as f:
        f.write(encrypted_payload)
        
    return output_path

def decrypt_file(encrypted_file_path: str, key: bytes, output_path: str = None) -> str:
    """
    Decrypt a .kcrypt file using AES-256-GCM and write to output path.
    Returns path to the decrypted file.
    """
    path = Path(encrypted_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
    with open(path, "rb") as f:
        encrypted_payload = f.read()
        
    decrypted_data = decrypt_bytes(encrypted_payload, key)
    
    if output_path is None:
        original_name = path.stem if path.name.endswith(".kcrypt") else f"decrypted_{path.name}"
        output_path = str(path.parent / f"restored_{original_name}")
        
    with open(output_path, "wb") as f:
        f.write(decrypted_data)
        
    return output_path

if __name__ == "__main__":
    test_key = os.urandom(32)
    sample_text = b"KolamCrypt Confidential Data Payload - AES-256 Verification"
    enc = encrypt_bytes(sample_text, test_key)
    dec = decrypt_bytes(enc, test_key)
    assert dec == sample_text, "Encryption/Decryption mismatch!"
    print("AES-256-GCM Encryption Module Verified Successfully.")
