import os
import hashlib
import math
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import config

def seed_to_int(seed_input) -> int:
    """Convert any string/bytes/int seed into a deterministic 32-bit integer."""
    if seed_input is None:
        seed_input = os.urandom(16)
    if isinstance(seed_input, str):
        seed_input = seed_input.encode('utf-8')
    if isinstance(seed_input, bytes):
        digest = hashlib.sha256(seed_input).digest()
        return int.from_bytes(digest[:4], byteorder='big')
    return int(seed_input) & 0xFFFFFFFF

def generate_kolam_image(seed=None, size=config.DEFAULT_IMAGE_SIZE) -> Image.Image:
    """
    Generate a procedural mathematical Kolam pattern image using grid dots, 
    radial symmetry, and smooth curves.
    
    Returns a crisp RGB PIL Image object.
    """
    seed_val = seed_to_int(seed)
    width, height = size
    
    # Create solid dark background image (RGB mode for universal compatibility)
    img = Image.new("RGB", (width, height), config.KOLAM_BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Grid settings
    grid_size = 7  # 7x7 dot matrix
    margin = width * 0.15
    spacing_x = (width - 2 * margin) / (grid_size - 1)
    spacing_y = (height - 2 * margin) / (grid_size - 1)
    
    center_x, center_y = width / 2.0, height / 2.0
    
    # Draw dots (Pulli grid)
    dots = []
    for r in range(grid_size):
        for c in range(grid_size):
            # Form a diamond or octagonal Kolam grid boundary
            dist_from_center = abs(r - (grid_size - 1)/2) + abs(c - (grid_size - 1)/2)
            if dist_from_center <= (grid_size - 1):
                px = margin + c * spacing_x
                py = margin + r * spacing_y
                dots.append((px, py))
                
                # Draw outer glow dot
                draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(244, 63, 94))
                # Draw bright center dot
                draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 255, 255))
                
    # Deterministic procedural loop generation using seed
    np.random.seed(seed_val)
    num_petals = 4 + 2 * (seed_val % 3)  # 4, 6, or 8 fold symmetry
    outer_radius = (width - 2 * margin) * 0.45
    inner_radius = outer_radius * 0.25
    
    # Primary symmetry loops (Cyan)
    points_curve = []
    steps = 360
    harmonic1 = 1 + (seed_val % 4)
    harmonic2 = 2 + ((seed_val >> 4) % 5)
    phase_shift = (seed_val % 360) * math.pi / 180.0
    
    for deg in range(steps + 1):
        rad = deg * math.pi / 180.0
        r = inner_radius + (outer_radius - inner_radius) * (
            0.5 + 0.3 * math.sin(num_petals * rad) +
            0.2 * math.cos(harmonic1 * num_petals * rad + phase_shift)
        )
        
        x = center_x + r * math.cos(rad)
        y = center_y + r * math.sin(rad)
        points_curve.append((x, y))
        
    if len(points_curve) > 1:
        draw.line(points_curve, fill=(56, 189, 248), width=3) # Bright Cyan
        
    # Secondary inner interlocking loops (Amber/Gold)
    sec_points = []
    sec_petals = num_petals * 2
    for deg in range(steps + 1):
        rad = deg * math.pi / 180.0
        r = inner_radius * 0.8 + (outer_radius * 0.4) * (
            0.5 + 0.5 * math.cos(sec_petals * rad + phase_shift)
        )
        x = center_x + r * math.cos(rad)
        y = center_y + r * math.sin(rad)
        sec_points.append((x, y))
        
    if len(sec_points) > 1:
        draw.line(sec_points, fill=(251, 191, 36), width=2) # Bright Amber
        
    # Outer geometric bounding loops (Purple accent)
    corner_points = []
    for i in range(num_petals):
        angle = (i * 2 * math.pi / num_petals) + (math.pi / 4)
        rx = center_x + (outer_radius * 1.05) * math.cos(angle)
        ry = center_y + (outer_radius * 1.05) * math.sin(angle)
        corner_points.append((rx, ry))
    corner_points.append(corner_points[0])
    
    draw.line(corner_points, fill=(168, 85, 247), width=2) # Bright Purple
    
    return img

def generate_kolam(seed=None, filename=None) -> str:
    """
    Generate a Kolam pattern and save to disk.
    Returns the absolute path to the generated PNG file.
    """
    config.ensure_directories()
    img = generate_kolam_image(seed=seed)
    
    if filename is None:
        seed_hash = hashlib.md5(str(seed_to_int(seed)).encode()).hexdigest()[:8]
        filename = f"kolam_{seed_hash}.png"
        
    output_path = config.KOLAM_OUTPUT_DIR / filename
    img.save(output_path, "PNG")
    return str(output_path)

def generate_kolam_base64(seed=None) -> str:
    """Generate Kolam pattern image as a Base64 data URI string."""
    img = generate_kolam_image(seed=seed)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

if __name__ == "__main__":
    path = generate_kolam("demo_seed_123")
    print(f"Kolam pattern generated successfully at: {path}")
