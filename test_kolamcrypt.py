import unittest
import os
import shutil
import uuid
from pathlib import Path
import config
from kolam_generator import generate_kolam, generate_kolam_image
from key_derivation import derive_key
from encryptor import encrypt_bytes, decrypt_bytes, encrypt_file, decrypt_file
from fragmenter import fragment_bytes, reassemble_fragment_bytes, verify_fragment, verify_fragment_hash
from cloud_storage import upload_fragment, download_fragment
from database import db

class TestKolamCryptSuite(unittest.TestCase):

    def setUp(self):
        config.ensure_directories()
        self.test_dir = config.TEMP_DIR / f"test_{uuid.uuid4().hex[:6]}"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.password = "SecureKolamPass2026!"
        self.seed = "test_kolam_seed_unit"
        self.kolam_path = generate_kolam(seed=self.seed, filename="test_kolam.png")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_1_small_file_roundtrip(self):
        """Test Case 1: Small text file encryption & decryption roundtrip."""
        sample_path = self.test_dir / "sample_small.txt"
        sample_text = b"Hello KolamCrypt! Small payload test."
        with open(sample_path, "wb") as f:
            f.write(sample_text)
            
        key, salt = derive_key(self.password, self.kolam_path)
        enc_path = encrypt_file(str(sample_path), key)
        
        dec_path = self.test_dir / "restored_small.txt"
        decrypt_file(enc_path, key, output_path=str(dec_path))
        
        with open(dec_path, "rb") as f:
            restored = f.read()
            
        self.assertEqual(restored, sample_text, "Decrypted small text payload does not match original!")

    def test_2_1mb_file_encryption(self):
        """Test Case 2: Encrypt 1 MB binary file -> success."""
        mb_path = self.test_dir / "sample_1mb.bin"
        one_mb_bytes = os.urandom(1024 * 1024)
        with open(mb_path, "wb") as f:
            f.write(one_mb_bytes)
            
        key, salt = derive_key(self.password, self.kolam_path)
        enc_path = encrypt_file(str(mb_path), key)
        
        self.assertTrue(os.path.exists(enc_path), "1 MB encrypted file was not created!")
        self.assertGreater(os.path.getsize(enc_path), 1024 * 1024, "Encrypted file size is too small.")

    def test_3_decrypt_correct_password(self):
        """Test Case 3: Decrypt with correct password -> success."""
        data = b"Confidential financial statement data."
        key, salt = derive_key(self.password, self.kolam_path)
        ciphertext = encrypt_bytes(data, key)
        
        # Derive key again with same password & salt
        key_rederived, _ = derive_key(self.password, self.kolam_path, salt=salt)
        decrypted = decrypt_bytes(ciphertext, key_rederived)
        self.assertEqual(decrypted, data)

    def test_4_decrypt_wrong_password(self):
        """Test Case 4: Decrypt with wrong password -> fail."""
        data = b"Confidential payload"
        key, salt = derive_key(self.password, self.kolam_path)
        ciphertext = encrypt_bytes(data, key)
        
        wrong_key, _ = derive_key("WRONG_PASSWORD_XYZ", self.kolam_path, salt=salt)
        
        with self.assertRaises(ValueError, msg="Should raise ValueError on wrong password decryption attempt."):
            decrypt_bytes(ciphertext, wrong_key)

    def test_5_fragment_upload_multi_cloud(self):
        """Test Case 5: Fragment upload to 3 multi-cloud locations -> success."""
        data = b"Multi cloud fragment payload" * 10
        frags = fragment_bytes(data, num_fragments=3)
        self.assertEqual(len(frags), 3)
        
        clouds = ["GoogleDrive", "Dropbox", "OneDrive"]
        for idx, frag in enumerate(frags):
            meta = upload_fragment(frag["raw_fragment"], clouds[idx], f"test_frag_{idx}.dat")
            self.assertEqual(meta["cloud_service"], clouds[idx])
            self.assertTrue(os.path.exists(meta["path"]))

    def test_6_reassemble_fragments(self):
        """Test Case 6: Reassemble fragments -> success."""
        original_data = b"Reassembly Verification Content Matrix" * 50
        key, salt = derive_key(self.password, self.kolam_path)
        ciphertext = encrypt_bytes(original_data, key)
        
        frags = fragment_bytes(ciphertext, num_fragments=3)
        raw_list = [f["raw_fragment"] for f in frags]
        
        reassembled_ciphertext = reassemble_fragment_bytes(raw_list)
        self.assertEqual(reassembled_ciphertext, ciphertext)
        
        restored = decrypt_bytes(reassembled_ciphertext, key)
        self.assertEqual(restored, original_data)

    def test_7_integrity_check_tampered_fragment(self):
        """Test Case 7: Integrity check with tampered fragment -> fail."""
        data = b"Fragment tampering detection payload"
        frags = fragment_bytes(data, num_fragments=3)
        target_frag = frags[0]
        
        expected_hash = target_frag["hash"]
        valid_before = verify_fragment_hash(target_frag["data"], expected_hash)
        self.assertTrue(valid_before, "Original fragment hash should be valid.")
        
        tampered_bytes = target_frag["data"] + b"TAMPERED"
        valid_after = verify_fragment_hash(tampered_bytes, expected_hash)
        self.assertFalse(valid_after, "Tampered fragment must fail integrity hash verification!")

if __name__ == "__main__":
    unittest.main(verbosity=2)
