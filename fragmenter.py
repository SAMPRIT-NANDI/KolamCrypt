import os
import hashlib
from pathlib import Path
import config

def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hex digest for a byte stream."""
    return hashlib.sha256(data).hexdigest()

def verify_fragment_hash(data: bytes, expected_hash: str) -> bool:
    """Verify fragment integrity against expected SHA-256 hash."""
    return compute_hash(data).lower() == expected_hash.lower()

def verify_fragment(fragment_path: str, expected_hash: str) -> bool:
    """Verify fragment file integrity on disk against expected SHA-256 hash."""
    path = Path(fragment_path)
    if not path.exists():
        return False
    with open(path, "rb") as f:
        content = f.read()
        
    # If fragment has header, extract payload for hash verification or compute raw hash
    if content.startswith(b"KFRAG|"):
        try:
            _, _, payload = content.split(b"|", 2)
            return compute_hash(payload).lower() == expected_hash.lower()
        except ValueError:
            return False
            
    return compute_hash(content).lower() == expected_hash.lower()

def fragment_bytes(encrypted_payload: bytes, num_fragments: int = config.DEFAULT_NUM_FRAGMENTS) -> list[dict]:
    """
    Split encrypted payload into N balanced fragments in-memory with SHA-256 checksums.
    
    Returns list of dicts:
    [
       {
          "index": 0,
          "total": N,
          "hash": "sha256...",
          "data": bytes,
          "raw_fragment": bytes_with_header
       }, ...
    ]
    """
    if num_fragments < 1:
        raise ValueError("Number of fragments must be at least 1.")
        
    total_len = len(encrypted_payload)
    chunk_size = (total_len + num_fragments - 1) // num_fragments
    
    fragments = []
    for i in range(num_fragments):
        start = i * chunk_size
        end = min(start + chunk_size, total_len)
        chunk_data = encrypted_payload[start:end]
        chunk_hash = compute_hash(chunk_data)
        
        # Header format: KFRAG|index/total|hash|
        header = f"KFRAG|{i}/{num_fragments}|{chunk_hash}|".encode('utf-8')
        raw_fragment = header + chunk_data
        
        fragments.append({
            "index": i,
            "total": num_fragments,
            "hash": chunk_hash,
            "data": chunk_data,
            "raw_fragment": raw_fragment
        })
        
    return fragments

def fragment_file(encrypted_file_path: str, num_fragments: int = config.DEFAULT_NUM_FRAGMENTS, output_dir: str = None) -> list[dict]:
    """
    Split an encrypted file into N fragment files saved on disk.
    
    Returns list of dicts containing fragment file paths, hashes, and indices.
    """
    path = Path(encrypted_file_path)
    if not path.exists():
        raise FileNotFoundError(f"File to fragment not found: {encrypted_file_path}")
        
    with open(path, "rb") as f:
        data = f.read()
        
    frags = fragment_bytes(data, num_fragments=num_fragments)
    
    out_dir = Path(output_dir) if output_dir else path.parent / f"{path.stem}_fragments"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fragment_info_list = []
    for frag in frags:
        frag_filename = f"{path.stem}.frag{frag['index'] + 1}of{num_fragments}"
        frag_file_path = out_dir / frag_filename
        
        with open(frag_file_path, "wb") as f:
            f.write(frag["raw_fragment"])
            
        frag_info_list.append({
            "index": frag["index"],
            "total": frag["total"],
            "hash": frag["hash"],
            "path": str(frag_file_path),
            "filename": frag_filename
        })
        
    return fragment_info_list

def reassemble_fragment_bytes(fragment_raw_bytes_list: list[bytes]) -> bytes:
    """
    Reassemble fragment byte objects into original encrypted payload.
    Automatically parses headers and orders fragments by index.
    """
    parsed_chunks = []
    for raw in fragment_raw_bytes_list:
        if not raw.startswith(b"KFRAG|"):
            raise ValueError("Malformed fragment: Missing KFRAG header.")
            
        parts = raw.split(b"|", 3)
        if len(parts) < 4:
            raise ValueError("Invalid fragment header format.")
            
        meta = parts[1].decode('utf-8') # e.g. "0/3"
        idx_str, _ = meta.split('/')
        idx = int(idx_str)
        expected_hash = parts[2].decode('utf-8')
        payload = parts[3]
        
        # Verify integrity
        if not verify_fragment_hash(payload, expected_hash):
            raise ValueError(f"Fragment integrity check failed for fragment index {idx}!")
            
        parsed_chunks.append((idx, payload))
        
    # Sort by index
    parsed_chunks.sort(key=lambda item: item[0])
    
    # Concatenate payloads
    return b"".join([chunk[1] for chunk in parsed_chunks])

def reassemble_fragments(fragment_paths: list[str], output_file_path: str = None) -> str:
    """
    Reassemble fragment files from disk into a single encrypted file.
    
    Args:
        fragment_paths: List of paths to fragment files.
        output_file_path: Path where assembled file should be written.
    """
    raw_list = []
    for p in fragment_paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"Fragment file missing: {p}")
        with open(path, "rb") as f:
            raw_list.append(f.read())
            
    reassembled_bytes = reassemble_fragment_bytes(raw_list)
    
    if output_file_path is None:
        first_path = Path(fragment_paths[0])
        output_file_path = str(first_path.parent / "reassembled_encrypted_file.kcrypt")
        
    with open(output_file_path, "wb") as f:
        f.write(reassembled_bytes)
        
    return output_file_path

if __name__ == "__main__":
    sample_payload = b"Sample Encrypted Data Payload for Fragmentation Test" * 5
    frags = fragment_bytes(sample_payload, num_fragments=3)
    raw_frags = [f["raw_fragment"] for f in frags]
    restored = reassemble_fragment_bytes(raw_frags)
    assert restored == sample_payload, "Fragment reassembly mismatch!"
    print("Fragmentation & Reassembly Module Verified Successfully.")
