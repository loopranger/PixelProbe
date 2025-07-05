import os
import uuid
import stripe
import json
from datetime import datetime
from io import BytesIO
from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Response
from flask_login import current_user
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
from app import app, db
from models import User, Image, Subscription
from replit_auth import require_login, make_replit_blueprint
from utils import allowed_file, get_image_dimensions, convert_rgb_to_hsl, determine_color_temperature

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Get the domain for Stripe redirects
YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN') 
if not YOUR_DOMAIN and os.environ.get('REPLIT_DEPLOYMENT') != 'true':
    domains = os.environ.get('REPLIT_DOMAINS')
    if domains:
        YOUR_DOMAIN = domains.split(',')[0]
        
if YOUR_DOMAIN:
    YOUR_DOMAIN = f"https://{YOUR_DOMAIN}"
else:
    YOUR_DOMAIN = "http://localhost:5000"  # fallback for local development

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
    images = Image.query.filter_by(user_id=user.id).order_by(
        Image.created_at.desc()).all()

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
            flash(
                f'You have reached your limit of {current_user.max_images} images. Please delete some images first.',
                'error')
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
                original_filename = secure_filename(file.filename
                                                    or "unknown.jpg")
                filename = f"{uuid.uuid4().hex}_{original_filename}"

                # Get image dimensions and validate using PIL from memory
                try:
                    with PILImage.open(BytesIO(file_data)) as img:
                        # Handle EXIF rotation
                        from PIL import ExifTags

                        # Get original dimensions
                        original_width, original_height = img.size

                        # Check for EXIF orientation
                        orientation = 1
                        try:
                            exif = img.getexif()
                            if exif is not None:
                                orientation = exif.get(
                                    ExifTags.Base.Orientation.value, 1)
                        except:
                            pass

                        # Adjust dimensions based on orientation
                        if orientation in [6, 8]:  # 90 or 270 degree rotation
                            width, height = original_height, original_width
                        else:
                            width, height = original_width, original_height

                        format_str = img.format.lower(
                        ) if img.format else "jpeg"
                        mime_type = f"image/{format_str}"
                except Exception as e:
                    flash('Invalid image file', 'error')
                    return redirect(url_for('upload'))

                # Create database record with image data
                image = Image(filename=filename,
                              original_filename=original_filename,
                              file_size=file_size,
                              mime_type=mime_type,
                              width=width,
                              height=height,
                              user_id=current_user.id,
                              image_data=file_data)

                db.session.add(image)
                db.session.commit()

                flash('Image uploaded successfully!', 'success')
                return redirect(url_for('profile'))

            except Exception as e:
                flash(f'Error uploading image: {str(e)}', 'error')
                return redirect(url_for('upload'))
        else:
            flash('Invalid file type. Please upload a valid image file.',
                  'error')
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

        # Check if image has blob data
        if not image.image_data:
            return jsonify({'error': 'Image data not available'}), 400

        # Open image from blob data and get pixel color
        with PILImage.open(BytesIO(image.image_data)) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Handle EXIF rotation to match frontend display
            from PIL import ExifTags

            # Get EXIF orientation
            orientation = 1
            try:
                exif = img.getexif()
                if exif is not None:
                    orientation = exif.get(ExifTags.Base.Orientation.value, 1)
            except:
                pass

            # Get original image dimensions
            original_width, original_height = img.size

            # Use stored display dimensions from database
            display_width, display_height = image.width, image.height

            # Transform coordinates based on orientation
            # Mind the difference of iOS and Android and some camera manufacturers seem to make compared to EXIF documentation: "The picture needs to be rotated x degrees for rendering."
            # vs "The picture is currently / was captured rotated x degrees."
            # further reading: https://exiftool.org/forum/index.php?topic=15404.0
            if orientation == 8:  # 90 degree clockwise rotation (smartphone context)
                #
                # For EXIF orientation 6: image is rotated 90° clockwise
                # Frontend coordinates are in display space, need to map to original image space
                actual_x = display_height - 1 - y
                actual_y = x
            elif orientation == 6:  # 90 degree counter-clockwise rotation (smartphone context)
                # For EXIF orientation 8: image is rotated 90° counter-clockwise
                actual_x = y
                actual_y = display_width - 1 - x
            else:
                # No rotation needed
                actual_x = x
                actual_y = y

            # Validate coordinates are within display bounds
            if x < 0 or x >= display_width or y < 0 or y >= display_height:
                return jsonify({
                    'error':
                    f'Coordinates ({x}, {y}) are outside image bounds ({display_width}x{display_height})'
                }), 400

            # Validate transformed coordinates are within actual image bounds
            if actual_x < 0 or actual_x >= original_width or actual_y < 0 or actual_y >= original_height:
                return jsonify({
                    'error':
                    f'Transformed coordinates ({actual_x}, {actual_y}) are outside actual image bounds ({original_width}x{original_height})'
                }), 400

            # Get pixel color using transformed coordinates
            rgb = img.getpixel((actual_x, actual_y))

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
                'coordinates': {
                    'x': x,
                    'y': y
                }
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
            'Content-Disposition':
            f'inline; filename="{image.original_filename}"',
            'Cache-Control': 'max-age=3600'  # Cache for 1 hour
        })


@app.route('/upgrade')
@require_login
def upgrade():
    """Upgrade to premium page with pricing information"""
    return render_template('upgrade.html', 
                         current_user=current_user,
                         has_subscription=current_user.has_active_subscription())


@app.route('/create-checkout-session', methods=['POST'])
@require_login
def create_checkout_session():
    """Create Stripe checkout session for premium subscription"""
    try:
        # Check if user already has an active subscription
        if current_user.has_active_subscription():
            flash('You already have an active subscription!', 'info')
            return redirect(url_for('profile'))
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': 'Color Analyzer Premium',
                            'description': 'Unlimited image storage and analysis',
                        },
                        'unit_amount': 399,  # €3.99 in cents
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=YOUR_DOMAIN + '/payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=YOUR_DOMAIN + '/upgrade',
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
            },
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        flash(f'Error creating checkout session: {str(e)}', 'error')
        return redirect(url_for('upgrade'))


@app.route('/payment-success')
@require_login
def payment_success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Invalid payment session.', 'error')
        return redirect(url_for('upgrade'))
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Get subscription details
            subscription = stripe.Subscription.retrieve(session.subscription)
            
            # Create or update subscription record
            existing_subscription = Subscription.query.filter_by(
                user_id=current_user.id,
                stripe_subscription_id=subscription.id
            ).first()
            
            if not existing_subscription:
                new_subscription = Subscription(
                    user_id=current_user.id,
                    stripe_subscription_id=subscription.id,
                    stripe_customer_id=subscription.customer,
                    status=subscription.status,
                    current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                    current_period_end=datetime.fromtimestamp(subscription.current_period_end)
                )
                db.session.add(new_subscription)
                db.session.commit()
            
            flash('Welcome to Premium! Your subscription is now active.', 'success')
            return render_template('payment_success.html')
        else:
            flash('Payment was not completed successfully.', 'error')
            return redirect(url_for('upgrade'))
            
    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')
        return redirect(url_for('upgrade'))


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Note: In production, you should verify the webhook signature
        # For now, we'll process the event without verification
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
        
        # Handle subscription events
        if event['type'] == 'customer.subscription.updated':
            subscription_data = event['data']['object']
            
            # Update subscription in database
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_data['id']
            ).first()
            
            if subscription:
                subscription.status = subscription_data['status']
                subscription.current_period_start = datetime.fromtimestamp(
                    subscription_data['current_period_start']
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    subscription_data['current_period_end']
                )
                db.session.commit()
                
        elif event['type'] == 'customer.subscription.deleted':
            subscription_data = event['data']['object']
            
            # Mark subscription as cancelled
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_data['id']
            ).first()
            
            if subscription:
                subscription.status = 'canceled'
                db.session.commit()
        
        return '', 200
        
    except Exception as e:
        print(f'Webhook error: {str(e)}')
        return '', 400


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(413)
def file_too_large(error):
    flash('File is too large. Maximum size is 15MB.', 'error')
    return redirect(url_for('upload'))
