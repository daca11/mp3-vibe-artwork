# MP3 Artwork Manager - Quick Start Guide

## 🚀 Quick Start

Get the MP3 Artwork Manager up and running in minutes!

### Prerequisites

- **Python 3.8+** (recommended: Python 3.9 or higher)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/daca11/mp3-vibe-artwork.git
cd mp3-vibe-artwork

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Start the Flask development server
python run.py
```

The application will start on **http://localhost:5001**

### 3. Using the Application

1. **Open your browser** to `http://localhost:5001`
2. **Upload MP3 files** using the drag & drop interface
3. **Monitor processing** in the queue page
4. **Select artwork** when processing completes
5. **Download** your enhanced MP3 files

---

## 📋 Detailed Setup Instructions

### System Requirements

- **Python**: 3.8+ (tested with 3.9-3.13)
- **Memory**: 512MB+ available RAM
- **Storage**: 100MB+ free space (more for processing large files)
- **Network**: Internet connection for MusicBrainz artwork search

### Dependencies Overview

The application uses these key libraries:
- **Flask** - Web framework
- **mutagen** - MP3 metadata manipulation
- **Pillow** - Image processing
- **musicbrainzngs** - MusicBrainz API client
- **requests** - HTTP requests
- **pytest** - Testing framework

### Environment Configuration

Create a `.env` file in the project root for custom configuration:

```bash
# Optional: Custom configuration
FLASK_ENV=development
MAX_CONTENT_LENGTH=52428800  # 50MB file upload limit
MUSICBRAINZ_RATE_LIMIT=1.0   # Requests per second
```

### Directory Structure

The application creates these directories automatically:
```
mp3-vibe-artwork/
├── uploads/     # Uploaded MP3 files
├── temp/        # Temporary processing files
├── output/      # Generated MP3 files with artwork
└── logs/        # Application logs (production mode)
```

---

## 🎵 Using the Application

### 1. File Upload

**Supported Formats:**
- MP3 files (.mp3)
- File size limit: 50MB per file
- Multiple file upload supported

**Upload Methods:**
- Drag & drop files onto the upload area
- Click "Choose Files" button to browse
- Multiple files can be selected at once

### 2. Processing Workflow

The application automatically:
1. **Validates** uploaded files
2. **Extracts** existing metadata and artwork
3. **Searches** MusicBrainz for additional artwork
4. **Optimizes** all artwork (resize to 500x500px, compress to <500KB)
5. **Presents** artwork options for selection

### 3. Artwork Selection

**Features:**
- Side-by-side artwork comparison
- Metadata display (resolution, file size, source)
- Preview with zoom capability
- Bulk selection strategies available

**Selection Strategies:**
- **Prefer Embedded** - Choose artwork from MP3 file
- **Prefer MusicBrainz** - Choose artwork from online database
- **Highest Resolution** - Automatically select best quality
- **Smallest File** - Choose most compressed option

### 4. Output Generation

**Options:**
- Individual file download
- Batch processing with ZIP archive
- Original filename preservation
- Metadata preservation with embedded artwork

---

## 🔧 Advanced Configuration

### Production Deployment

For production use, consider:

```bash
# Set production environment
export FLASK_ENV=production

# Run with Gunicorn (install separately)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### Custom Configuration

Edit `config.py` for advanced settings:

```python
class Config:
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # Image optimization settings
    MAX_IMAGE_SIZE = (500, 500)  # pixels
    MAX_IMAGE_FILE_SIZE = 500 * 1024  # 500KB
    
    # MusicBrainz settings
    MUSICBRAINZ_RATE_LIMIT = 1.0  # requests per second
    MUSICBRAINZ_TIMEOUT = 10  # seconds
```

### Background Processing

The application supports background processing for large batches:

- **Task Management**: View running tasks at `/api/tasks`
- **Bulk Operations**: Process multiple files simultaneously
- **Progress Tracking**: Real-time updates for long operations

---

## 🧪 Testing

Run the test suite to verify everything works:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_phase2_upload.py -v  # Upload tests
python -m pytest tests/test_integration.py -v    # Integration tests

# Run with coverage (install pytest-cov first)
pip install pytest-cov
python -m pytest --cov=app tests/
```

---

## 🛠️ Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**2. Port Already in Use**
```bash
# Kill existing processes
pkill -f "python run.py"

# Or change port in run.py
app.run(host='0.0.0.0', port=5002, debug=True)
```

**3. Permission Errors**
```bash
# Ensure write permissions for upload directories
chmod 755 uploads temp output
```

**4. MusicBrainz API Issues**
- Check internet connection
- Verify MusicBrainz service status
- Reduce rate limit in configuration

### Debug Mode

Enable detailed logging:

```python
# In run.py
import logging
logging.basicConfig(level=logging.DEBUG)
app.run(host='0.0.0.0', port=5001, debug=True)
```

### Performance Optimization

For better performance with large files:

1. **Increase memory limits** in system configuration
2. **Use SSD storage** for temp directories
3. **Adjust image quality settings** in config
4. **Enable concurrent processing** for bulk operations

---

## 📚 API Documentation

The application provides RESTful APIs:

### Key Endpoints

- `POST /api/upload` - Upload MP3 files
- `GET /api/queue` - View processing queue
- `POST /api/process/{file_id}` - Process individual file
- `GET /api/artwork/{file_id}` - Get artwork options
- `POST /api/artwork/{file_id}/select` - Select artwork
- `POST /api/output/{file_id}` - Generate output file
- `GET /api/download/{file_id}` - Download processed file

### Bulk Operations

- `POST /api/bulk/process` - Bulk file processing
- `POST /api/bulk/artwork-select` - Bulk artwork selection
- `POST /api/bulk/output` - Bulk output generation
- `GET /api/bulk/strategies` - Available selection strategies

### Task Management

- `GET /api/tasks` - List all background tasks
- `GET /api/tasks/{task_id}` - Get task status
- `POST /api/tasks/{task_id}/cancel` - Cancel task
- `GET /api/tasks/stats` - Task statistics

---

## 🎯 Next Steps

1. **Upload your first MP3 files** and try the complete workflow
2. **Explore bulk operations** for processing multiple files
3. **Check the processing queue** to monitor progress
4. **Experiment with artwork selection** strategies
5. **Download and enjoy** your enhanced MP3 files!

---

## 📞 Support

If you encounter issues:

1. **Check the logs** in the application output
2. **Verify file formats** are supported MP3 files
3. **Test with smaller files** first
4. **Review the troubleshooting section** above
5. **Check GitHub issues** for known problems

The MP3 Artwork Manager is designed to be user-friendly and robust. Most workflows should complete successfully without manual intervention!

---

**Happy organizing your MP3 collection! 🎵✨**
