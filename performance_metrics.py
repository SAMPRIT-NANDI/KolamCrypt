import time
import os
import matplotlib.pyplot as plt
import numpy as np
import config
from kolam_generator import generate_kolam
from key_derivation import derive_key
from encryptor import encrypt_bytes, decrypt_bytes

def run_performance_benchmarks():
    print("=" * 60)
    print("      K O L A M C R Y P T   P E R F O R M A N C E   B E N C H M A R K      ")
    print("=" * 60)
    
    # Payload sizes: 64KB, 256KB, 1MB, 4MB, 10MB
    sizes_bytes = [64 * 1024, 256 * 1024, 1024 * 1024, 4 * 1024 * 1024, 10 * 1024 * 1024]
    sizes_mb = [s / (1024 * 1024) for s in sizes_bytes]
    
    enc_times_ms = []
    dec_times_ms = []
    throughput_mbps = []
    
    kolam_path = generate_kolam("benchmark_seed_2026")
    key, _ = derive_key("BenchmarkPassword123!", kolam_path)
    
    print("\nExecuting throughput benchmarks across 5 payload sizes...\n")
    print(f"{'Size (MB)':<12} | {'Enc Time (ms)':<15} | {'Dec Time (ms)':<15} | {'Throughput (MB/s)':<18}")
    print("-" * 65)
    
    for s_bytes, s_mb in zip(sizes_bytes, sizes_mb):
        dummy_data = os.urandom(s_bytes)
        
        # Benchmark Encryption
        t0 = time.perf_counter()
        encrypted = encrypt_bytes(dummy_data, key)
        t_enc = (time.perf_counter() - t0) * 1000.0
        enc_times_ms.append(t_enc)
        
        # Benchmark Decryption
        t0 = time.perf_counter()
        decrypted = decrypt_bytes(encrypted, key)
        t_dec = (time.perf_counter() - t0) * 1000.0
        dec_times_ms.append(t_dec)
        
        # Throughput
        tp = s_mb / ((t_enc / 1000.0) if t_enc > 0 else 0.001)
        throughput_mbps.append(tp)
        
        print(f"{s_mb:<12.2f} | {t_enc:<15.2f} | {t_dec:<15.2f} | {tp:<18.2f}")
        
    print("-" * 65)
    
    # Generate Charts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Encryption & Decryption Time
    ax1.plot(sizes_mb, enc_times_ms, 'o-', color='#38bdf8', linewidth=2, label='AES-256-GCM Encrypt (ms)')
    ax1.plot(sizes_mb, dec_times_ms, 's-', color='#f43f5e', linewidth=2, label='AES-256-GCM Decrypt (ms)')
    ax1.set_xlabel('File Payload Size (MB)', fontsize=11)
    ax1.set_ylabel('Execution Time (milliseconds)', fontsize=11)
    ax1.set_title('KolamCrypt Latency vs File Size', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Plot 2: Cloud Fragment Distribution Overhead
    clouds = ['Google Drive', 'Dropbox', 'OneDrive']
    overhead_pct = [33.3, 33.3, 33.4] # Balanced shards
    colors = ['#4285F4', '#0061FF', '#0078D4']
    
    ax2.bar(clouds, overhead_pct, color=colors, width=0.5)
    ax2.set_ylabel('Shard Distribution (%)', fontsize=11)
    ax2.set_title('Multi-Cloud Fragment Storage Balance', fontsize=12, fontweight='bold')
    ax2.set_ylim(0, 50)
    for i, v in enumerate(overhead_pct):
        ax2.text(i, v + 1, f"{v}%", ha='center', fontweight='bold')
        
    plt.tight_layout()
    chart_output_path = config.BASE_DIR / "performance_charts.png"
    plt.savefig(chart_output_path, dpi=300)
    plt.close()
    
    print(f"\n[OK] Benchmark charts saved to: {chart_output_path}\n")

if __name__ == "__main__":
    run_performance_benchmarks()
