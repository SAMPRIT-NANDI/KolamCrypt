import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Cloud Simulation Directories
CLOUD_SIM_DIR = BASE_DIR / "cloud_sim"
DRIVE_DIR = CLOUD_SIM_DIR / "drive"
DROPBOX_DIR = CLOUD_SIM_DIR / "dropbox"
ONEDRIVE_DIR = CLOUD_SIM_DIR / "onedrive"

CLOUD_SERVICES = {
    "GoogleDrive": DRIVE_DIR,
    "Dropbox": DROPBOX_DIR,
    "OneDrive": ONEDRIVE_DIR
}

# Output and Asset Directories
KOLAM_OUTPUT_DIR = BASE_DIR / "kolam_patterns"
TEMP_DIR = BASE_DIR / "temp"

# Database Configuration
DB_PATH = BASE_DIR / "kolamcrypt.db"

# Cryptographic Constants
AES_KEY_SIZE = 32          # 256 bits
AES_IV_SIZE = 16           # 128 bits
SALT_SIZE = 16             # 128 bits salt for PBKDF2
PBKDF2_ITERATIONS = 100000 # Standard PBKDF2 iterations

# Kolam Generator Settings
DEFAULT_IMAGE_SIZE = (256, 256)
KOLAM_BG_COLOR = (15, 23, 42)      # Slate Dark Blue #0f172a
KOLAM_LINE_COLOR = (56, 189, 248)   # Cyan #38bdf8
KOLAM_DOT_COLOR = (244, 63, 94)     # Rose #f43f5e

# Fragmentation Defaults
DEFAULT_NUM_FRAGMENTS = 3

def ensure_directories():
    """Ensure all required runtime directories exist."""
    directories = [
        CLOUD_SIM_DIR,
        DRIVE_DIR,
        DROPBOX_DIR,
        ONEDRIVE_DIR,
        KOLAM_OUTPUT_DIR,
        TEMP_DIR
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Auto-initialize directories on import
ensure_directories()
