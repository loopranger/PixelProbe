import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize the app with the extension
db.init_app(app)

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize scheduler for cleanup tasks
scheduler = BackgroundScheduler()

def cleanup_expired_images():
    """Clean up expired images for free users"""
    with app.app_context():
        from models import Image, User
        from datetime import datetime, timedelta
        import os
        
        # Find expired images (24 hours old for free users)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        expired_images = db.session.query(Image).join(User).filter(
            User.is_premium == False,
            Image.created_at < cutoff_time
        ).all()
        
        for image in expired_images:
            # Delete file from filesystem
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted expired image file: {file_path}")
            
            # Delete database record
            db.session.delete(image)
        
        db.session.commit()
        logging.info(f"Cleaned up {len(expired_images)} expired images")

# Schedule cleanup to run every hour
scheduler.add_job(
    func=cleanup_expired_images,
    trigger=IntervalTrigger(hours=1),
    id='cleanup_expired_images',
    name='Cleanup expired images for free users',
    replace_existing=True
)

# Start the scheduler
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

with app.app_context():
    # Import models to ensure tables are created
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
