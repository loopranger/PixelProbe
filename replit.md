# Color Analyzer

## Overview

Color Analyzer is a Flask-based web application that allows users to upload images and analyze colors at the pixel level. Users can click on any pixel within their uploaded images to get detailed color information including hex values, HSL values, and color temperature classification (warm/cold). The application features a freemium model with different storage limits for free and premium users.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQL-based using SQLAlchemy with declarative base models
- **Authentication**: Replit Auth integration with Flask-Dance OAuth
- **Session Management**: Flask-Login for user session handling
- **Background Tasks**: APScheduler for cleanup operations
- **File Upload**: Werkzeug secure file handling with 15MB size limit

### Frontend Architecture
- **Template Engine**: Jinja2 with Flask
- **CSS Framework**: Bootstrap with dark theme
- **Icons**: Feather icons
- **Interactive Features**: Custom JavaScript for color picking and image upload
- **Canvas API**: HTML5 Canvas for pixel-level color analysis

### Authentication System
- Uses Replit Auth as the primary authentication provider
- OAuth token storage in database linked to user sessions
- Session storage with browser session keys for security
- Login required decorators for protected routes

## Key Components

### Models (`models.py`)
- **User Model**: Stores user information with premium status and image relationships
  - Supports freemium model (3 images for free, 50 for premium)
  - Auto-generated display names and profile management
- **OAuth Model**: Required for Replit Auth integration
- **Image Model**: Stores uploaded image metadata and file information

### Routes (`routes.py`)
- **Authentication Routes**: Login/logout via Replit Auth
- **File Upload**: Secure image upload with validation and storage limits
- **Image Viewing**: Interactive color analysis interface
- **Profile Management**: User dashboard with image management

### Utilities (`utils.py`)
- **File Validation**: Supports PNG, JPG, JPEG, GIF, BMP, WEBP formats
- **Image Processing**: PIL-based dimension extraction and color analysis
- **Color Conversion**: RGB to HSL conversion with temperature classification

### Client-Side Features
- **Color Picker**: Interactive canvas-based pixel color selection
- **Image Upload**: Drag-and-drop interface with preview functionality
- **Real-time Analysis**: Instant color information display on pixel click

## Data Flow

1. **User Authentication**: Users authenticate via Replit Auth OAuth flow
2. **Image Upload**: Files are validated, processed, and stored in uploads directory
3. **Image Analysis**: Images are rendered on HTML5 canvas for interactive analysis
4. **Color Extraction**: JavaScript extracts pixel data and sends to backend for processing
5. **Color Information**: Backend processes RGB values and returns hex, HSL, and temperature data

## External Dependencies

### Python Packages
- Flask ecosystem (Flask, Flask-SQLAlchemy, Flask-Login, Flask-Dance)
- PIL (Pillow) for image processing
- APScheduler for background tasks
- JWT for token handling
- Werkzeug for security utilities

### Frontend Libraries
- Bootstrap CSS framework with dark theme
- Feather Icons for UI elements
- HTML5 Canvas API for image manipulation

### Authentication
- Replit Auth OAuth provider integration
- Flask-Dance for OAuth flow management

## Deployment Strategy

### Environment Configuration
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: Database connection string
- File uploads stored in local `uploads/` directory
- Maximum file size limit of 15MB

### Database Setup
- SQLAlchemy with declarative base models
- Connection pooling with 300-second recycle time
- Pre-ping enabled for connection health checks

### Background Tasks
- APScheduler configured for cleanup operations
- Automated expired image deletion for free users
- Graceful shutdown handling with atexit registration

## Changelog
```
Changelog:
- July 02, 2025. Initial setup
- July 02, 2025. Updated color temperature analysis logic:
  * Cold: lightness = 0
  * Warm: lightness = 100  
  * Neutral: saturation = 0
  * Warm: hue 0-90 or 270-359 degrees
  * Cold: all other hue values
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```