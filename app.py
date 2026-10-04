import streamlit as st
import os
import uuid
import time
from pathlib import Path
from PIL import Image
import config
from kolam_generator import generate_kolam_image, generate_kolam
from key_derivation import derive_key_from_bytes, derive_key
from encryptor import encrypt_bytes, decrypt_bytes, encrypt_file, decrypt_file
from fragmenter import fragment_bytes, reassemble_fragment_bytes, verify_fragment_hash
from cloud_storage import upload_fragment, download_fragment, cloud_manager
from database import db

# Page Configuration
st.set_page_config(
    page_title="KolamCrypt - Secure AI Kolam Encryption",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Neon Aesthetics)
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎨 KolamCrypt Security Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Inspired Kolam Pattern File Encryption & Multi-Cloud Fragmented Storage System</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "🔒 Encrypt & Store", 
    "🔓 Retrieve & Decrypt", 
    "🖼️ Kolam Pattern Gallery", 
    "☁️ Cloud Fragment Inspector", 
    "📊 Performance Metrics"
])

# ==========================================
# TAB 1: ENCRYPT & STORE
# ==========================================
with tabs[0]:
    st.subheader("Encrypt File with Procedural Kolam Key Derivation")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Choose a file to encrypt", type=None)
        password = st.text_input("Encryption Password", type="password", key="enc_pass")
        custom_seed = st.text_input("Kolam Pattern Seed (Optional)", placeholder="Leave empty for random seed", key="enc_seed")
        num_fragments = st.slider("Number of Cloud Fragments", min_value=2, max_value=6, value=3)
        
        encrypt_btn = st.button("✨ Generate Kolam & Encrypt File", type="primary", use_container_width=True)

    with col2:
        st.markdown("### Live Kolam Pattern Preview")
        preview_seed = custom_seed if custom_seed else (password if password else "preview_kolam_seed")
        preview_img = generate_kolam_image(seed=preview_seed)
        st.image(preview_img, caption=f"Generated Pattern (Seed: {preview_seed[:12]})", use_container_width=True)

    if encrypt_btn:
        if not uploaded_file:
            st.error("Please select a file to encrypt!")
        elif not password:
            st.error("Please enter an encryption password!")
        else:
            with st.spinner("Executing KolamCrypt Encryption Pipeline..."):
                t0 = time.time()
                file_bytes = uploaded_file.getvalue()
                filename = uploaded_file.name
                file_size = len(file_bytes)
                
                seed_used = custom_seed if custom_seed else f"seed_{uuid.uuid4().hex[:8]}"
                file_id = f"KC-{uuid.uuid4().hex[:8]}"
                
                # 1. Generate Kolam
                kolam_path = generate_kolam(seed=seed_used, filename=f"kolam_{file_id}.png")
                
                # 2. Derive Key
                key, salt = derive_key(password, kolam_path)
                salt_hex = salt.hex()
                
                # 3. Encrypt
                encrypted_payload = encrypt_bytes(file_bytes, key)
                
                # 4. Fragment
                frags = fragment_bytes(encrypted_payload, num_fragments=num_fragments)
                
                # 5. Distribute to Cloud
                cloud_services = list(config.CLOUD_SERVICES.keys())
                uploaded_frags_meta = []
                
                for idx, frag in enumerate(frags):
                    cloud_svc = cloud_services[idx % len(cloud_services)]
                    target_name = f"{file_id}_frag{frag['index']+1}.dat"
                    
                    meta = upload_fragment(frag["raw_fragment"], cloud_svc, target_filename=target_name)
                    uploaded_frags_meta.append({
                        "index": frag["index"],
                        "cloud_service": cloud_svc,
                        "cloud_file_id": target_name,
                        "hash": frag["hash"]
                    })
                    
                # 6. Save DB record
                db.save_file_record(
                    file_id=file_id,
                    filename=filename,
                    file_size=file_size,
                    salt_hex=salt_hex,
                    seed=seed_used,
                    kolam_path=kolam_path,
                    fragments=uploaded_frags_meta
                )
                
                t_total = time.time() - t0
                
            st.success(f"🎉 File successfully encrypted & fragmented in {t_total*1000:.2f} ms!")
            st.info(f"**File ID:** `{file_id}` (Save this ID to decrypt later)")
            
            st.markdown("### Cloud Fragment Distribution Map")
            f_cols = st.columns(len(uploaded_frags_meta))
            for i, fmeta in enumerate(uploaded_frags_meta):
                with f_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>Fragment #{fmeta['index']+1}</h4>
                        <p><b>Cloud:</b> {fmeta['cloud_service']}</p>
                        <p><b>File ID:</b> {fmeta['cloud_file_id']}</p>
                        <p><b>SHA-256:</b> <code>{fmeta['hash'][:10]}...</code></p>
                    </div>
                    """, unsafe_allow_html=True)

# ==========================================
# TAB 2: RETRIEVE & DECRYPT
# ==========================================
with tabs[1]:
    st.subheader("Retrieve Shards & Decrypt File")
    
    files_list = db.list_files()
    if not files_list:
        st.info("No encrypted files in database yet. Encrypt a file first!")
    else:
        file_options = {f"{f['filename']} (ID: {f['file_id']})": f['file_id'] for f in files_list}
        selected_option = st.selectbox("Select Encrypted File Record", list(file_options.keys()))
        selected_file_id = file_options[selected_option]
        
        dec_password = st.text_input("Enter Decryption Password", type="password", key="dec_pass")
        
        decrypt_btn = st.button("🔓 Retrieve & Decrypt", type="primary")
        
        if decrypt_btn:
            if not dec_password:
                st.error("Please enter the decryption password!")
            else:
                record = db.get_file_record(selected_file_id)
                with st.spinner("Downloading fragments & verifying integrity..."):
                    try:
                        raw_fragments = []
                        frag_status = []
                        
                        for frag_meta in record["fragments"]:
                            svc = frag_meta["cloud_service"]
                            cloud_fid = frag_meta["cloud_file_id"]
                            expected_hash = frag_meta["fragment_hash"]
                            
                            # Download from cloud
                            frag_raw = download_fragment(cloud_fid, svc)
                            
                            # Parse payload from raw fragment
                            parts = frag_raw.split(b"|", 3)
                            payload = parts[3]
                            
                            valid = verify_fragment_hash(payload, expected_hash)
                            frag_status.append((cloud_fid, svc, valid))
                            raw_fragments.append(frag_raw)
                            
                        # Check integrity
                        all_valid = all(s[2] for s in frag_status)
                        if not all_valid:
                            st.error("❌ Integrity Verification Failed! One or more fragments were tampered with.")
                        else:
                            # Reassemble
                            ciphertext_payload = reassemble_fragment_bytes(raw_fragments)
                            
                            # Derive key using stored Kolam pattern & password
                            kolam_path = record["kolam"]["pattern_image_path"]
                            salt = bytes.fromhex(record["salt_hex"])
                            
                            key, _ = derive_key(dec_password, kolam_path, salt=salt)
                            
                            # Decrypt payload
                            restored_bytes = decrypt_bytes(ciphertext_payload, key)
                            
                            st.success("✅ File Successfully Decrypted & Restored!")
                            st.download_button(
                                label=f"📥 Download Decrypted {record['filename']}",
                                data=restored_bytes,
                                file_name=f"restored_{record['filename']}",
                                mime="application/octet-stream"
                            )
                    except ValueError as err:
                        st.error(f"❌ Decryption Failed: {err}. Check if password is correct.")
                    except Exception as ex:
                        st.error(f"❌ Error during retrieval: {ex}")

# ==========================================
# TAB 3: KOLAM GALLERY
# ==========================================
with tabs[2]:
    st.subheader("Generated AI/Procedural Kolam Patterns")
    files_list = db.list_files()
    if not files_list:
        st.info("No Kolam patterns stored yet.")
    else:
        g_cols = st.columns(3)
        for idx, file_rec in enumerate(files_list):
            rec = db.get_file_record(file_rec["file_id"])
            kolam_info = rec["kolam"]
            
            with g_cols[idx % 3]:
                if os.path.exists(kolam_info["pattern_image_path"]):
                    img = Image.open(kolam_info["pattern_image_path"])
                    st.image(img, caption=f"File: {file_rec['filename']}", use_container_width=True)
                    st.caption(f"**Seed:** `{file_rec['seed']}` | **File ID:** `{file_rec['file_id']}`")
                else:
                    st.warning("Pattern image file missing.")

# ==========================================
# TAB 4: CLOUD FRAGMENT INSPECTOR
# ==========================================
with tabs[3]:
    st.subheader("Simulated Multi-Cloud Fragment Storage Inspection")
    cloud_items = cloud_manager.list_cloud_fragments()
    
    if not cloud_items:
        st.info("No cloud fragments currently stored.")
    else:
        c1, c2, c3 = st.columns(3)
        for svc_name, col in zip(["GoogleDrive", "Dropbox", "OneDrive"], [c1, c2, c3]):
            with col:
                st.markdown(f"### ☁️ {svc_name}")
                svc_items = [i for i in cloud_items if i["cloud_service"] == svc_name]
                if not svc_items:
                    st.caption("No shards stored here.")
                for item in svc_items:
                    st.markdown(f"""
                    <div class="metric-card">
                        📄 <b>{item['filename']}</b><br/>
                        <small>Size: {item['size']} bytes</small>
                    </div>
                    <br/>
                    """, unsafe_allow_html=True)

# ==========================================
# TAB 5: PERFORMANCE METRICS
# ==========================================
with tabs[4]:
    st.subheader("System Performance & Cryptographic Metrics")
    st.markdown("Run automated performance benchmark across varying file payload sizes.")
    
    if st.button("🚀 Run Performance Benchmark"):
        with st.spinner("Measuring encryption/decryption throughput..."):
            sizes = [100*1024, 500*1024, 1024*1024, 2*1024*1024]
            enc_times = []
            dec_times = []
            
            dummy_kolam_path = generate_kolam("benchmark_seed")
            test_key, _ = derive_key("bench_pass", dummy_kolam_path)
            
            for s in sizes:
                data = os.urandom(s)
                # Encrypt timing
                t0 = time.time()
                enc_data = encrypt_bytes(data, test_key)
                enc_times.append((time.time() - t0) * 1000)
                
                # Decrypt timing
                t0 = time.time()
                decrypt_bytes(enc_data, test_key)
                dec_times.append((time.time() - t0) * 1000)
                
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 4))
            size_mb = [s / (1024*1024) for s in sizes]
            
            ax.plot(size_mb, enc_times, marker='o', color='#38bdf8', label='Encryption Time (ms)')
            ax.plot(size_mb, dec_times, marker='s', color='#f43f5e', label='Decryption Time (ms)')
            ax.set_xlabel('File Payload Size (MB)')
            ax.set_ylabel('Execution Time (ms)')
            ax.set_title('KolamCrypt Throughput Performance')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.5)
            
            st.pyplot(fig)
            
            st.markdown("""
            **Cryptographic Key Space Analysis:**
            - **Algorithm:** AES-256-GCM (Authenticated Encryption)
            - **Key Derivation:** PBKDF2 with HMAC-SHA256 (100,000 Iterations) + Kolam Image SHA-256 Digest
            - **Key Space:** $2^{256}$ (~$1.15 \\times 10^{77}$ combinations)
            - **Fragment Integrity:** 256-bit SHA-256 checksum per shard.
            """)
