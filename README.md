# MP3 Artwork Manager

A comprehensive web application for automatically managing and enhancing MP3 file artwork. Upload your MP3 collection, automatically extract and optimize artwork, search MusicBrainz for additional artwork options, and download enhanced files with embedded artwork.

## ✨ Features

- **🎵 MP3 File Processing**: Upload and process multiple MP3 files simultaneously
- **🎨 Artwork Management**: Extract, optimize, and embed artwork in MP3 files
- **🔍 MusicBrainz Integration**: Automatically search for high-quality artwork online
- **📱 Modern Web Interface**: Responsive design with real-time progress tracking
- **⚡ Batch Operations**: Process multiple files with bulk selection strategies
- **🔧 Background Processing**: Non-blocking task management for large operations
- **📊 Comprehensive Monitoring**: Task tracking, progress indicators, and detailed logging

## 🚀 Quick Start

**Get started in 2 minutes:**

```bash
# Clone and setup
git clone https://github.com/daca11/mp3-vibe-artwork.git
cd mp3-vibe-artwork

# Auto setup (Linux/macOS)
./setup.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the application
python run.py
```

**Open your browser to [http://localhost:5001](http://localhost:5001)** and start uploading MP3 files!

For detailed instructions, see **[QUICKSTART.md](QUICKSTART.md)**.

## 🐳 Docker Quick Start

```bash
# Using Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t mp3-artwork-manager .
docker run -p 5001:5001 -v $(pwd)/uploads:/app/uploads mp3-artwork-manager
```

## 📋 System Requirements

- **Python 3.8+** (recommended: 3.9 or higher)
- **500MB+ RAM** (1GB+ recommended for large files)
- **Internet connection** (for MusicBrainz artwork search)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

## 🎯 How It Works

1. **Upload** - Drag & drop MP3 files or use the file browser
2. **Process** - Automatic metadata extraction and artwork analysis
3. **Search** - MusicBrainz integration finds additional artwork options
4. **Select** - Compare and choose the best artwork for each file
5. **Download** - Get your enhanced MP3 files with embedded artwork

## 🛠️ Architecture

**Backend Services:**
- Flask web framework with RESTful API design
- Mutagen for MP3 metadata manipulation
- Pillow for image processing and optimization
- MusicBrainz integration with rate limiting
- Background task processing with threading

**Frontend:**
- Bootstrap-based responsive web interface
- Real-time progress tracking with JavaScript
- Interactive artwork comparison and selection
- Drag & drop file upload with progress indicators

**Key Components:**
- `MP3Processor` - Metadata extraction and ID3 tag handling
- `ImageOptimizer` - Image resizing, compression, and format conversion
- `MusicBrainzService` - API integration with caching and error handling
- `TaskManager` - Background processing with progress tracking
- `BulkOperationsService` - Multi-file operations with selection strategies

## 📚 API Documentation

The application provides comprehensive RESTful APIs:

### Core Endpoints
- `POST /api/upload` - Upload MP3 files
- `GET /api/queue` - View processing queue
- `POST /api/process/{id}` - Process individual file
- `GET /api/artwork/{id}` - Get artwork options
- `POST /api/artwork/{id}/select` - Select artwork
- `POST /api/output/{id}` - Generate output file
- `GET /api/download/{id}` - Download processed file

### Bulk Operations
- `POST /api/bulk/process` - Bulk file processing
- `POST /api/bulk/artwork-select` - Bulk artwork selection
- `GET /api/bulk/strategies` - Available selection strategies

### Task Management
- `GET /api/tasks` - List background tasks
- `GET /api/tasks/{id}` - Get task status
- `POST /api/tasks/{id}/cancel` - Cancel task

## 🧪 Testing

Comprehensive test suite with 135+ tests:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_integration.py -v    # End-to-end tests
python -m pytest tests/test_phase*_*.py -v      # Component tests

# Run with coverage
pip install pytest-cov
python -m pytest --cov=app tests/
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional configuration
FLASK_ENV=development              # development/production
MAX_CONTENT_LENGTH=52428800        # 50MB file upload limit
MUSICBRAINZ_RATE_LIMIT=1.0         # Requests per second
MUSICBRAINZ_TIMEOUT=10             # API timeout in seconds
```

### Advanced Settings

Edit `config.py` for detailed configuration:

```python
class Config:
    # File processing
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # Image optimization
    MAX_IMAGE_SIZE = (500, 500)           # Max dimensions
    MAX_IMAGE_FILE_SIZE = 500 * 1024      # Max file size (500KB)
    IMAGE_QUALITY = 90                    # JPEG quality (1-100)
    
    # MusicBrainz integration
    MUSICBRAINZ_RATE_LIMIT = 1.0          # Requests per second
    MUSICBRAINZ_TIMEOUT = 10              # Timeout in seconds
    MUSICBRAINZ_MAX_RESULTS = 3           # Max artwork results
```

## 🚀 Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### Using Docker

```bash
# Production deployment with Docker Compose
docker-compose -f docker-compose.yml up -d
```

### Performance Recommendations

- Use SSD storage for temp directories
- Allocate 1GB+ RAM for large file processing
- Configure reverse proxy (nginx) for production
- Enable logging and monitoring
- Set up regular cleanup of temp files

## 🐛 Troubleshooting

**Common Issues:**

1. **Port already in use**: Change port in `run.py` or kill existing processes
2. **Permission errors**: Ensure write permissions for upload directories
3. **MusicBrainz timeouts**: Check internet connection and reduce rate limit
4. **Memory issues**: Process smaller batches or increase system memory

**Debug Mode:**

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed troubleshooting steps.

## 📖 Project Structure

```
mp3-vibe-artwork/
├── app/                    # Application code
│   ├── models/            # Data models (FileQueue, ProcessingJob)
│   ├── routes/            # API endpoints (upload, processing, artwork)
│   ├── services/          # Business logic (MP3, Image, MusicBrainz)
│   └── utils/             # Utilities (validation, helpers)
├── static/                # Frontend assets (CSS, JavaScript)
├── templates/             # HTML templates
├── tests/                 # Test suite (135+ tests)
├── uploads/               # Uploaded MP3 files
├── temp/                  # Temporary processing files
├── output/                # Generated files with artwork
└── logs/                  # Application logs
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Ensure all tests pass (`python -m pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎵 Acknowledgments

- **MusicBrainz** - For providing the comprehensive music database and Cover Art Archive
- **Mutagen** - For excellent MP3 metadata manipulation capabilities
- **Pillow** - For powerful image processing features
- **Flask** - For the robust web framework foundation

---

**Ready to enhance your MP3 collection? Get started with the [Quick Start Guide](QUICKSTART.md)!** 🎵✨
