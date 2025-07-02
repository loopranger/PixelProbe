import os
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_image_dimensions(file_path):
    """Get image dimensions using PIL"""
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None, None

def convert_rgb_to_hsl(r, g, b):
    """Convert RGB values to HSL"""
    r, g, b = r/255.0, g/255.0, b/255.0
    
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    
    # Calculate lightness
    l = (max_val + min_val) / 2
    
    if diff == 0:
        h = s = 0  # achromatic
    else:
        # Calculate saturation
        s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
        
        # Calculate hue
        if max_val == r:
            h = (g - b) / diff + (6 if g < b else 0)
        elif max_val == g:
            h = (b - r) / diff + 2
        else:  # max_val == b
            h = (r - g) / diff + 4
        
        h /= 6
    
    # Convert to degrees and percentages
    h = h * 360
    s = s * 100
    l = l * 100
    
    return h, s, l

def determine_color_temperature(hue, saturation, lightness):
    """Determine if a color is warm, cold, or neutral based on HSL values"""
    # Check lightness first
    if lightness == 0:
        return 'cold'
    elif lightness == 100:
        return 'warm'
    elif saturation == 0:
        return 'neutral'
    elif (0 <= hue <= 90) or (270 <= hue <= 359):
        return 'warm'
    else:
        return 'cold'

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
