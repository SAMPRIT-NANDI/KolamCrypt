import sys
import os
import uuid
from pathlib import Path
import config
from kolam_generator import generate_kolam
from key_derivation import derive_key
from encryptor import encrypt_file, decrypt_file
from fragmenter import fragment_file, reassemble_fragments, verify_fragment
from cloud_storage import upload_fragment, download_fragment, delete_fragment
from database import db

def print_banner():
    print("=" * 60)
    print("        K O L A M C R Y P T   S E C U R I T Y   S U I T E        ")
    print("  AI/Math Kolam Encryption & Multi-Cloud Fragmented Storage    ")
    print("=" * 60)

def encrypt_and_store_workflow():
    print("\n--- ENCRYPT & MULTI-CLOUD STORE FILE ---")
    file_path = input("Enter path to file to encrypt: ").strip('"\' ')
    if not os.path.exists(file_path):
        print(f"[!] Error: File not found at '{file_path}'")
        return
        
    password = input("Enter encryption password: ").strip()
    if not password:
        print("[!] Error: Password cannot be empty.")
        return
        
    seed_input = input("Enter custom seed for Kolam pattern (optional, press Enter for auto): ").strip()
    if not seed_input:
        seed_input = f"seed_{uuid.uuid4().hex[:8]}"
        
    print("\n[1/6] Generating unique procedural Kolam pattern...")
    file_id = f"KC-{uuid.uuid4().hex[:8]}"
    kolam_path = generate_kolam(seed=seed_input, filename=f"kolam_{file_id}.png")
    print(f"      [✓] Kolam pattern created: {kolam_path}")
    
    print("[2/6] Deriving 256-bit AES key via PBKDF2 (100,000 iterations)...")
    key, salt = derive_key(password, kolam_path)
    salt_hex = salt.hex()
    print(f"      [✓] Derived AES key digest: {key[:8].hex()}... (Salt: {salt_hex[:8]}...)")
    
    print("[3/6] Encrypting file using AES-256-GCM...")
    temp_encrypted_path = config.TEMP_DIR / f"{file_id}.kcrypt"
    encrypt_file(file_path, key, output_path=str(temp_encrypted_path))
    file_size = os.path.getsize(file_path)
    print(f"      [✓] Payload encrypted ({file_size} bytes)")
    
    print("[4/6] Fragmenting payload into 3 multi-cloud shards...")
    fragments_info = fragment_file(str(temp_encrypted_path), num_fragments=3)
    
    print("[5/6] Distributing fragments across multi-cloud simulated storage...")
    cloud_services = list(config.CLOUD_SERVICES.keys())
    uploaded_fragments = []
    
    for idx, frag in enumerate(fragments_info):
        cloud_svc = cloud_services[idx % len(cloud_services)]
        target_name = f"{file_id}_frag{frag['index']+1}.dat"
        meta = upload_fragment(frag["path"], cloud_svc, target_filename=target_name)
        
        uploaded_fragments.append({
            "index": frag["index"],
            "cloud_service": cloud_svc,
            "cloud_file_id": target_name,
            "hash": frag["hash"]
        })
        print(f"      [✓] Fragment #{frag['index']+1} stored in [{cloud_svc}] (SHA-256: {frag['hash'][:12]}...)")
        
    # Clean up local temporary encryption files
    if os.path.exists(temp_encrypted_path):
        os.remove(temp_encrypted_path)
        
    print("[6/6] Writing file metadata to database...")
    db.save_file_record(
        file_id=file_id,
        filename=Path(file_path).name,
        file_size=file_size,
        salt_hex=salt_hex,
        seed=seed_input,
        kolam_path=kolam_path,
        fragments=uploaded_fragments
    )
    
    print("\n=======================================================")
    print(f" [SUCCESS] FILE ENCRYPTED & DISTRIBUTED SECURELY!")
    print(f" File ID: {file_id}")
    print(f" Kolam Pattern: {kolam_path}")
    print("=======================================================\n")

def retrieve_and_decrypt_workflow():
    print("\n--- RETRIEVE & DECRYPT FILE ---")
    files = db.list_files()
    if not files:
        print("[!] No encrypted file records found in database.")
        return
        
    print("\nAvailable Encrypted Files:")
    for f in files:
        print(f"  • ID: {f['file_id']} | Name: {f['filename']} | Size: {f['file_size']} bytes | Created: {f['created_at']}")
        
    file_id = input("\nEnter File ID to retrieve: ").strip()
    record = db.get_file_record(file_id)
    if not record:
        print(f"[!] Error: File record '{file_id}' not found.")
        return
        
    password = input(f"Enter decryption password for '{record['filename']}': ").strip()
    
    print("\n[1/5] Fetching fragments from multi-cloud storage...")
    downloaded_frag_paths = []
    temp_frag_dir = config.TEMP_DIR / f"retrieve_{file_id}"
    temp_frag_dir.mkdir(parents=True, exist_ok=True)
    
    for frag_meta in record["fragments"]:
        svc = frag_meta["cloud_service"]
        cloud_fid = frag_meta["cloud_file_id"]
        expected_hash = frag_meta["fragment_hash"]
        
        local_frag_path = temp_frag_dir / cloud_fid
        print(f"      Downloading fragment '{cloud_fid}' from [{svc}]...")
        download_fragment(cloud_fid, svc, local_output_path=str(local_frag_path))
        
        # Integrity verification
        if not verify_fragment(str(local_frag_path), expected_hash):
            print(f"[!] CRITICAL INTEGRITY FAILURE: Fragment '{cloud_fid}' has been tampered with or corrupted!")
            return
            
        print(f"      [✓] Integrity Verified (SHA-256 match)")
        downloaded_frag_paths.append(str(local_frag_path))
        
    print("[2/5] Reassembling fragments into unified ciphertext payload...")
    reassembled_temp = config.TEMP_DIR / f"reassembled_{file_id}.kcrypt"
    reassemble_fragments(downloaded_frag_paths, output_file_path=str(reassembled_temp))
    print("      [✓] Ciphertext reassembled.")
    
    print("[3/5] Reconstructing key using stored Kolam pattern & input password...")
    kolam_path = record["kolam"]["pattern_image_path"]
    salt = bytes.fromhex(record["salt_hex"])
    
    try:
        key, _ = derive_key(password, kolam_path, salt=salt)
    except Exception as e:
        print(f"[!] Key derivation failed: {e}")
        return
        
    print("[4/5] Decrypting file payload with AES-256-GCM...")
    restored_output_path = config.TEMP_DIR / f"restored_{record['filename']}"
    
    try:
        decrypt_file(str(reassembled_temp), key, output_path=str(restored_output_path))
    except ValueError as err:
        print(f"\n[!] DECRYPTION FAILED: {err}")
        print("    (Check if password is correct and Kolam pattern image is intact.)")
        return
        
    print("[5/5] Cleanup temporary files...")
    if os.path.exists(reassembled_temp):
        os.remove(reassembled_temp)
        
    print("\n=======================================================")
    print(f" [SUCCESS] FILE SUCCESSFULLY DECRYPTED & RESTORED!")
    print(f" Restored File Saved At: {restored_output_path}")
    print("=======================================================\n")

def view_stored_files():
    print("\n--- STORED FILES & KOLAM PATTERNS ---")
    files = db.list_files()
    if not files:
        print("No files stored yet.")
        return
        
    for f in files:
        rec = db.get_file_record(f['file_id'])
        print(f"\n[File ID: {f['file_id']}]")
        print(f"  Filename     : {f['filename']}")
        print(f"  Size         : {f['file_size']} bytes")
        print(f"  Seed         : {f['seed']}")
        print(f"  Kolam Image  : {rec['kolam']['pattern_image_path']}")
        print("  Fragments    :")
        for frag in rec['fragments']:
            print(f"    - Frag #{frag['fragment_index']+1}: Cloud=[{frag['cloud_service']}] | FileID={frag['cloud_file_id']}")

def main():
    print_banner()
    while True:
        print("\nMAIN MENU:")
        print("1. Encrypt & Store File")
        print("2. Retrieve & Decrypt File")
        print("3. View Stored Files & Kolam Patterns")
        print("4. Exit")
        choice = input("\nSelect Option (1-4): ").strip()
        
        if choice == "1":
            encrypt_and_store_workflow()
        elif choice == "2":
            retrieve_and_decrypt_workflow()
        elif choice == "3":
            view_stored_files()
        elif choice == "4":
            print("\nExiting KolamCrypt. Goodbye!")
            sys.exit(0)
        else:
            print("[!] Invalid option. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
