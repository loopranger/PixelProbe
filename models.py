from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to images
    images = db.relationship('Image', backref='user', lazy=True, cascade='all, delete-orphan')
    
    @property
    def display_name(self):
        """Get display name for the user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.email:
            return self.email.split('@')[0]
        else:
            return f"User {self.id}"
    
    @property
    def max_images(self):
        """Get maximum number of images user can have"""
        return 50 if self.has_active_subscription() else 3
    
    def has_active_subscription(self):
        """Check if user has an active subscription"""
        # Check for active subscription first
        active_subscription = db.session.query(Subscription).filter_by(
            user_id=self.id,
            status='active'
        ).filter(
            Subscription.current_period_end >= datetime.utcnow()
        ).first()
        
        # Return True if subscription is active OR if is_premium is manually set
        return active_subscription is not None or self.is_premium
    
    @property
    def image_count(self):
        """Get current number of images user has"""
        return db.session.query(Image).filter_by(user_id=self.id).count()
    
    def can_upload_image(self):
        """Check if user can upload another image"""
        return self.image_count < self.max_images

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def expires_at(self):
        """Get expiration time for free users"""
        user = db.session.query(User).filter_by(id=self.user_id).first()
        if user and user.has_active_subscription():
            return None
        from datetime import timedelta
        return self.created_at + timedelta(hours=24)
    
    @property
    def is_expired(self):
        """Check if image is expired"""
        user = db.session.query(User).filter_by(id=self.user_id).first()
        if user and user.has_active_subscription():
            return False
        return self.expires_at and datetime.utcnow() > self.expires_at


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String, nullable=False, unique=True)
    stripe_customer_id = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)  # active, canceled, past_due, etc.
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='subscriptions')
    
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == 'active' and datetime.utcnow() <= self.current_period_end
