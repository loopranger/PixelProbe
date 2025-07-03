class ColorPicker {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.image = null;
        this.imageId = null;
        this.scale = 1;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.canvas.addEventListener('click', (e) => {
            this.handleClick(e);
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            this.handleMouseMove(e);
        });
        
        // Add crosshair cursor
        this.canvas.style.cursor = 'crosshair';
    }
    
    loadImage(imageSrc, imageId) {
        this.imageId = imageId;
        this.image = new Image();
        this.image.crossOrigin = 'anonymous';
        
        this.image.onload = () => {
            this.drawImage();
        };
        
        this.image.onerror = () => {
            console.error('Failed to load image');
            this.showError('Failed to load image');
        };
        
        this.image.src = imageSrc;
    }
    
    drawImage() {
        const maxWidth = this.canvas.parentElement.clientWidth - 40;
        const maxHeight = 600;
        
        let { width, height } = this.image;
        
        // Calculate scaling to fit within bounds
        const scaleX = maxWidth / width;
        const scaleY = maxHeight / height;
        this.scale = Math.min(scaleX, scaleY, 1);
        
        width *= this.scale;
        height *= this.scale;
        
        this.canvas.width = width;
        this.canvas.height = height;
        
        this.ctx.drawImage(this.image, 0, 0, width, height);
    }
    
    handleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        
        // Get click position relative to canvas
        const canvasX = e.clientX - rect.left;
        const canvasY = e.clientY - rect.top;
        
        // Account for the actual canvas size vs displayed size
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        
        // Get actual canvas coordinates
        const actualCanvasX = canvasX * scaleX;
        const actualCanvasY = canvasY * scaleY;
        
        // Convert to original image coordinates
        const x = Math.floor((actualCanvasX / this.canvas.width) * this.image.width);
        const y = Math.floor((actualCanvasY / this.canvas.height) * this.image.height);
        
        // Debug logging
        console.log('Click debug:', {
            clientClick: { x: e.clientX, y: e.clientY },
            rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
            canvasClick: { x: canvasX, y: canvasY },
            scale: { x: scaleX, y: scaleY },
            actualCanvas: { x: actualCanvasX, y: actualCanvasY },
            canvasSize: { width: this.canvas.width, height: this.canvas.height },
            imageSize: { width: this.image.width, height: this.image.height },
            finalCoords: { x, y }
        });
        
        // Ensure coordinates are within image bounds
        const imageWidth = this.image.width;
        const imageHeight = this.image.height;
        
        if (x >= 0 && x < imageWidth && y >= 0 && y < imageHeight) {
            this.analyzePixel(x, y);
        }
    }
    
    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        
        // Get mouse position relative to canvas
        const canvasX = e.clientX - rect.left;
        const canvasY = e.clientY - rect.top;
        
        // Account for the actual canvas size vs displayed size
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        
        // Get actual canvas coordinates
        const actualCanvasX = canvasX * scaleX;
        const actualCanvasY = canvasY * scaleY;
        
        // Convert to original image coordinates
        const x = Math.floor((actualCanvasX / this.canvas.width) * this.image.width);
        const y = Math.floor((actualCanvasY / this.canvas.height) * this.image.height);
        
        // Update tooltip or status if needed
        this.canvas.title = `Click to analyze pixel at (${x}, ${y})`;
    }
    
    async analyzePixel(x, y) {
        try {
            this.showLoading();
            
            const response = await fetch(`/image/${this.imageId}/color`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ x, y })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.displayColorInfo(data);
            
        } catch (error) {
            console.error('Error analyzing pixel:', error);
            this.showError('Failed to analyze pixel color');
        }
    }
    
    displayColorInfo(data) {
        const colorAnalysis = document.getElementById('colorAnalysis');
        const colorInfo = document.getElementById('colorInfo');
        
        // Hide initial message and show color info
        colorAnalysis.style.display = 'none';
        colorInfo.style.display = 'block';
        
        // Update color swatch
        const colorSwatch = document.getElementById('colorSwatch');
        colorSwatch.style.backgroundColor = data.hex;
        
        // Update coordinates
        document.getElementById('coordinates').textContent = `${data.coordinates.x}, ${data.coordinates.y}`;
        
        // Update color values
        document.getElementById('hexValue').textContent = data.hex;
        document.getElementById('rgbValue').textContent = `rgb(${data.rgb[0]}, ${data.rgb[1]}, ${data.rgb[2]})`;
        document.getElementById('hslValue').textContent = `hsl(${data.hsl.h}, ${data.hsl.s}%, ${data.hsl.l}%)`;
        
        // Update temperature
        const temperatureBadge = document.getElementById('temperatureBadge');
        const temperatureValue = document.getElementById('temperatureValue');
        
        temperatureValue.textContent = data.temperature;
        
        // Update badge color based on temperature
        temperatureBadge.className = 'badge';
        if (data.temperature === 'warm') {
            temperatureBadge.classList.add('bg-warning', 'text-dark');
        } else if (data.temperature === 'cold') {
            temperatureBadge.classList.add('bg-info', 'text-dark');
        } else if (data.temperature === 'neutral') {
            temperatureBadge.classList.add('bg-secondary', 'text-light');
        }
        
        // Add visual feedback on canvas
        this.drawCrosshair(data.coordinates.x, data.coordinates.y);
    }
    
    drawCrosshair(x, y) {
        // Redraw image first
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.drawImage(this.image, 0, 0, this.canvas.width, this.canvas.height);
        
        // Convert original image coordinates to canvas coordinates
        const canvasX = (x / this.image.width) * this.canvas.width;
        const canvasY = (y / this.image.height) * this.canvas.height;
        
        this.ctx.strokeStyle = '#fff';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        // Vertical line
        this.ctx.beginPath();
        this.ctx.moveTo(canvasX, 0);
        this.ctx.lineTo(canvasX, this.canvas.height);
        this.ctx.stroke();
        
        // Horizontal line
        this.ctx.beginPath();
        this.ctx.moveTo(0, canvasY);
        this.ctx.lineTo(this.canvas.width, canvasY);
        this.ctx.stroke();
        
        // Reset line dash
        this.ctx.setLineDash([]);
        
        // Draw center point
        this.ctx.fillStyle = '#fff';
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 2;
        
        this.ctx.beginPath();
        this.ctx.arc(canvasX, canvasY, 6, 0, 2 * Math.PI);
        this.ctx.fill();
        this.ctx.stroke();
    }
    
    showLoading() {
        const colorAnalysis = document.getElementById('colorAnalysis');
        const colorInfo = document.getElementById('colorInfo');
        
        colorInfo.style.display = 'none';
        colorAnalysis.style.display = 'block';
        colorAnalysis.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Analyzing color...</p>
            </div>
        `;
    }
    
    showError(message) {
        const colorAnalysis = document.getElementById('colorAnalysis');
        const colorInfo = document.getElementById('colorInfo');
        
        colorInfo.style.display = 'none';
        colorAnalysis.style.display = 'block';
        colorAnalysis.innerHTML = `
            <div class="text-center text-danger">
                <i data-feather="alert-circle" style="width: 48px; height: 48px;"></i>
                <p class="mt-2">${message}</p>
            </div>
        `;
        
        // Re-initialize feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

// Utility functions for color conversion
function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function rgbToHsl(r, g, b) {
    r /= 255;
    g /= 255;
    b /= 255;
    
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const diff = max - min;
    
    let h, s, l = (max + min) / 2;
    
    if (diff === 0) {
        h = s = 0;
    } else {
        s = l > 0.5 ? diff / (2 - max - min) : diff / (max + min);
        
        switch (max) {
            case r: h = (g - b) / diff + (g < b ? 6 : 0); break;
            case g: h = (b - r) / diff + 2; break;
            case b: h = (r - g) / diff + 4; break;
        }
        h /= 6;
    }
    
    return [h * 360, s * 100, l * 100];
}

function determineColorTemperature(hue, saturation, lightness) {
    // Check lightness first
    if (lightness === 0) {
        return 'cold';
    } else if (lightness === 100) {
        return 'warm';
    } else if (saturation === 0) {
        return 'neutral';
    } else if ((hue >= 0 && hue <= 90) || (hue >= 270 && hue <= 359)) {
        return 'warm';
    } else {
        return 'cold';
    }
}

// Make ColorPicker available globally
window.ColorPicker = ColorPicker;
