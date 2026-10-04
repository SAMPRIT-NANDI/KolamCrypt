import sys
from pathlib import Path

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uuid
import base64
import os

from kolam_generator import generate_kolam_image, generate_kolam_base64, generate_kolam
from key_derivation import derive_key_from_bytes, hash_kolam_bytes
from encryptor import encrypt_bytes, decrypt_bytes
from fragmenter import fragment_bytes, reassemble_fragment_bytes, verify_fragment_hash

app = FastAPI(title="KolamCrypt API", description="AI/Mathematical Kolam Pattern Encryption Serverless API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "KolamCrypt Cryptographic Engine", "version": "1.0.0"}

@app.post("/api/generate-kolam")
def api_generate_kolam(seed: str = Form(None)):
    """Generate Kolam pattern image as Base64 data URI."""
    if not seed:
        seed = f"seed_{uuid.uuid4().hex[:8]}"
    base64_img = generate_kolam_base64(seed=seed)
    return {"seed": seed, "image_data_uri": base64_img}

@app.post("/api/encrypt")
async def api_encrypt(
    file: UploadFile = File(...),
    password: str = Form(...),
    seed: str = Form(None),
    num_fragments: int = Form(3)
):
    """Encrypt uploaded file bytes using Kolam key derivation & return fragments."""
    try:
        file_bytes = await file.read()
        if not password:
            raise HTTPException(status_code=400, detail="Password is required.")
            
        seed_used = seed if seed else f"seed_{uuid.uuid4().hex[:8]}"
        file_id = f"KC-{uuid.uuid4().hex[:8]}"
        
        # Render Kolam in memory
        img = generate_kolam_image(seed=seed_used)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        kolam_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Derive key
        key, salt = derive_key_from_bytes(password, image_bytes)
        
        # Encrypt payload
        ciphertext = encrypt_bytes(file_bytes, key)
        
        # Fragment payload
        frags = fragment_bytes(ciphertext, num_fragments=num_fragments)
        cloud_services = ["GoogleDrive", "Dropbox", "OneDrive"]
        
        output_fragments = []
        for idx, fmeta in enumerate(frags):
            svc = cloud_services[idx % len(cloud_services)]
            frag_base64 = base64.b64encode(fmeta["raw_fragment"]).decode('utf-8')
            output_fragments.append({
                "index": fmeta["index"],
                "cloud_service": svc,
                "cloud_file_id": f"{file_id}_frag{fmeta['index']+1}.dat",
                "hash": fmeta["hash"],
                "fragment_base64": frag_base64
            })
            
        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "file_size": len(file_bytes),
            "salt_hex": salt.hex(),
            "seed": seed_used,
            "kolam_base64": f"data:image/png;base64,{kolam_base64}",
            "fragments": output_fragments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/decrypt")
async def api_decrypt(
    fragments_json: str = Form(...),
    password: str = Form(...),
    seed: str = Form(...),
    salt_hex: str = Form(...)
):
    """Decrypt payload from JSON list of raw fragment base64 strings."""
    import json
    try:
        frag_list = json.loads(fragments_json) # List of base64 strings
        raw_fragments = [base64.b64decode(item) for item in frag_list]
        
        # Reassemble
        ciphertext = reassemble_fragment_bytes(raw_fragments)
        
        # Render Kolam for key derivation
        img = generate_kolam_image(seed=seed)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        
        salt = bytes.fromhex(salt_hex)
        key, _ = derive_key_from_bytes(password, image_bytes, salt=salt)
        
        restored_bytes = decrypt_bytes(ciphertext, key)
        restored_b64 = base64.b64encode(restored_bytes).decode('utf-8')
        
        return {
            "status": "success",
            "restored_base64": restored_b64
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
