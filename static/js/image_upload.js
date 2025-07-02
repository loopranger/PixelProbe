document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const filePreview = document.getElementById('filePreview');
    const previewImage = document.getElementById('previewImage');
    const fileInfo = document.getElementById('fileInfo');
    
    // File input change handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileSelection(file);
        }
    });
    
    // Drag and drop functionality
    const uploadZone = document.querySelector('.upload-zone') || document.body;
    
    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (isValidImageFile(file)) {
                fileInput.files = files;
                handleFileSelection(file);
            } else {
                showError('Please select a valid image file');
            }
        }
    });
    
    // Form submission handler
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file to upload');
            return;
        }
        
        if (!isValidImageFile(file)) {
            showError('Please select a valid image file');
            return;
        }
        
        if (file.size > 15 * 1024 * 1024) {
            showError('File size must be less than 15MB');
            return;
        }
        
        uploadFile(file);
    });
    
    function handleFileSelection(file) {
        // Validate file
        if (!isValidImageFile(file)) {
            showError('Please select a valid image file');
            return;
        }
        
        if (file.size > 15 * 1024 * 1024) {
            showError('File size must be less than 15MB');
            return;
        }
        
        // Show file info
        const fileSize = formatFileSize(file.size);
        fileInfo.textContent = `${file.name} (${fileSize})`;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            filePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
    
    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        // Show progress
        uploadProgress.style.display = 'block';
        uploadBtn.disabled = true;
        
        // Create XMLHttpRequest for progress tracking
        const xhr = new XMLHttpRequest();
        
        // Upload progress handler
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                const progressBar = uploadProgress.querySelector('.progress-bar');
                progressBar.style.width = percentComplete + '%';
                progressBar.textContent = Math.round(percentComplete) + '%';
            }
        });
        
        // Response handler
        xhr.onload = function() {
            if (xhr.status === 200) {
                // Success - redirect will be handled by the server
                window.location.href = '/profile';
            } else {
                showError('Upload failed. Please try again.');
                resetUploadForm();
            }
        };
        
        // Error handler
        xhr.onerror = function() {
            showError('Upload failed. Please check your connection and try again.');
            resetUploadForm();
        };
        
        // Send request
        xhr.open('POST', uploadForm.action);
        xhr.send(formData);
    }
    
    function isValidImageFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
        return allowedTypes.includes(file.type);
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    function showError(message) {
        // Create or update error alert
        let errorAlert = document.querySelector('.alert-danger');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-danger alert-dismissible fade show';
            errorAlert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').prepend(errorAlert);
        } else {
            errorAlert.textContent = message;
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (errorAlert.parentNode) {
                errorAlert.remove();
            }
        }, 5000);
    }
    
    function resetUploadForm() {
        uploadProgress.style.display = 'none';
        uploadBtn.disabled = false;
        
        const progressBar = uploadProgress.querySelector('.progress-bar');
        progressBar.style.width = '0%';
        progressBar.textContent = '';
    }
});

// File size validation
function validateFileSize(file) {
    const maxSize = 15 * 1024 * 1024; // 15MB
    if (file.size > maxSize) {
        return false;
    }
    return true;
}

// Image dimension validation
function validateImageDimensions(file, callback) {
    const img = new Image();
    img.onload = function() {
        const width = this.width;
        const height = this.height;
        
        // Optional: Add dimension limits if needed
        const maxWidth = 10000;
        const maxHeight = 10000;
        
        if (width > maxWidth || height > maxHeight) {
            callback(false, `Image dimensions too large. Maximum: ${maxWidth}x${maxHeight}`);
        } else {
            callback(true, null);
        }
    };
    
    img.onerror = function() {
        callback(false, 'Invalid image file');
    };
    
    img.src = URL.createObjectURL(file);
}

// Utility function to create image thumbnail
function createImageThumbnail(file, maxWidth = 200, maxHeight = 200) {
    return new Promise((resolve, reject) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = function() {
            // Calculate new dimensions
            let { width, height } = img;
            
            if (width > height) {
                if (width > maxWidth) {
                    height *= maxWidth / width;
                    width = maxWidth;
                }
            } else {
                if (height > maxHeight) {
                    width *= maxHeight / height;
                    height = maxHeight;
                }
            }
            
            canvas.width = width;
            canvas.height = height;
            
            // Draw resized image
            ctx.drawImage(img, 0, 0, width, height);
            
            // Convert to blob
            canvas.toBlob(resolve, 'image/jpeg', 0.8);
        };
        
        img.onerror = reject;
        img.src = URL.createObjectURL(file);
    });
}

// Initialize upload functionality
window.ImageUpload = {
    validateFileSize,
    validateImageDimensions,
    createImageThumbnail
};
