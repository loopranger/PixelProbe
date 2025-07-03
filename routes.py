import os
import uuid
from datetime import datetime
from io import BytesIO
from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Response
from flask_login import current_user
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
from app import app, db
from models import User, Image
from replit_auth import require_login, make_replit_blueprint
from utils import allowed_file, get_image_dimensions, convert_rgb_to_hsl, determine_color_temperature

# Register Replit Auth blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

@app.route('/')
def index():
    """Landing page - shows different content based on authentication status"""
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return render_template('index.html')

@app.route('/profile')
@require_login
def profile():
    """User profile page showing uploaded images"""
    user = current_user
    images = Image.query.filter_by(user_id=user.id).order_by(Image.created_at.desc()).all()
    
    return render_template('profile.html', 
                         user=user, 
                         images=images,
                         now=datetime.utcnow())

@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """Image upload page"""
    if request.method == 'POST':
        # Check if user can upload more images
        if not current_user.can_upload_image():
            flash(f'You have reached your limit of {current_user.max_images} images. Please delete some images first.', 'error')
            return redirect(url_for('upload'))
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('upload'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload'))
        
        if file and allowed_file(file.filename):
            try:
                # Read file data into memory
                file_data = file.read()
                file_size = len(file_data)
                
                # Generate unique filename identifier
                original_filename = secure_filename(file.filename or "unknown.jpg")
                filename = f"{uuid.uuid4().hex}_{original_filename}"
                
                # Get image dimensions and validate using PIL from memory
                try:
                    with PILImage.open(BytesIO(file_data)) as img:
                        width, height = img.size
                        format_str = img.format.lower() if img.format else "jpeg"
                        mime_type = f"image/{format_str}"
                except Exception as e:
                    flash('Invalid image file', 'error')
                    return redirect(url_for('upload'))
                
                # Create database record with image data
                image = Image(
                    filename=filename,
                    original_filename=original_filename,
                    file_size=file_size,
                    mime_type=mime_type,
                    width=width,
                    height=height,
                    user_id=current_user.id,
                    image_data=file_data
                )
                
                db.session.add(image)
                db.session.commit()
                
                flash('Image uploaded successfully!', 'success')
                return redirect(url_for('profile'))
                
            except Exception as e:
                flash(f'Error uploading image: {str(e)}', 'error')
                return redirect(url_for('upload'))
        else:
            flash('Invalid file type. Please upload a valid image file.', 'error')
            return redirect(url_for('upload'))
    
    return render_template('upload.html')

@app.route('/image/<int:image_id>')
@require_login
def view_image(image_id):
    """View image with color picker functionality"""
    image = Image.query.get_or_404(image_id)
    
    # Check if user owns this image
    if image.user_id != current_user.id:
        flash('You do not have permission to view this image.', 'error')
        return redirect(url_for('profile'))
    
    # Check if image is expired
    if image.is_expired:
        flash('This image has expired.', 'error')
        return redirect(url_for('profile'))
    
    return render_template('view_image.html', image=image)

@app.route('/image/<int:image_id>/color', methods=['POST'])
@require_login
def get_pixel_color(image_id):
    """Get color information for a specific pixel"""
    image = Image.query.get_or_404(image_id)
    
    # Check if user owns this image
    if image.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if image is expired
    if image.is_expired:
        return jsonify({'error': 'Image has expired'}), 404
    
    try:
        data = request.get_json()
        x = int(data['x'])
        y = int(data['y'])
        
        # Open image and get pixel color
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
        with PILImage.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get pixel color
            rgb = img.getpixel((x, y))
            
            # Convert to hex
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            
            # Convert to HSL
            hsl = convert_rgb_to_hsl(rgb[0], rgb[1], rgb[2])
            
            # Determine color temperature
            temperature = determine_color_temperature(hsl[0], hsl[1], hsl[2])
            
            return jsonify({
                'rgb': rgb,
                'hex': hex_color,
                'hsl': {
                    'h': round(hsl[0]),
                    's': round(hsl[1]),
                    'l': round(hsl[2])
                },
                'temperature': temperature,
                'coordinates': {'x': x, 'y': y}
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/image/<int:image_id>/delete', methods=['POST'])
@require_login
def delete_image(image_id):
    """Delete an image"""
    image = Image.query.get_or_404(image_id)
    
    # Check if user owns this image
    if image.user_id != current_user.id:
        flash('You do not have permission to delete this image.', 'error')
        return redirect(url_for('profile'))
    
    try:
        # Delete from database (image data is stored as blob, no file system cleanup needed)
        db.session.delete(image)
        db.session.commit()
        
        flash('Image deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting image: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/uploads/<filename>')
@require_login
def uploaded_file(filename):
    """Serve uploaded files from database blob"""
    # Additional security check - ensure user owns the image
    image = Image.query.filter_by(filename=filename).first_or_404()
    
    if image.user_id != current_user.id:
        return "Unauthorized", 403
    
    if image.is_expired:
        return "Image has expired", 404
    
    # Create response with image data from database
    return Response(
        image.image_data,
        mimetype=image.mime_type,
        headers={
            'Content-Disposition': f'inline; filename="{image.original_filename}"',
            'Cache-Control': 'max-age=3600'  # Cache for 1 hour
        }
    )

@app.route('/upgrade')
@require_login
def upgrade():
    """Upgrade to premium page (placeholder for future payment integration)"""
    return render_template('upgrade.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(413)
def file_too_large(error):
    flash('File is too large. Maximum size is 15MB.', 'error')
    return redirect(url_for('upload'))
