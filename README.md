# MP3 Artwork Manager for Traktor 3

A web-based application that analyzes MP3 files, resizes embedded ID3 artwork to meet Traktor 3 specifications, and fetches missing artwork using the MusicBrainz API.

## Features

- Process single MP3 files or entire folders
- Resize artwork to Traktor 3 specifications (≤500x500px, ≤500KB)
- Fetch missing artwork from MusicBrainz API
- Web-based interface for easy file management
- Preserve original files (creates processed copies)

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Modern web browser
- Internet connection (for MusicBrainz API)

### 2. Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Application

```bash
# Make sure virtual environment is activated
python app.py

# Open browser and navigate to:
# http://localhost:5001
```

### 4. Deactivating Virtual Environment

```bash
deactivate
```

## Traktor 3 Artwork Specifications

- Maximum dimensions: 500x500 pixels
- Maximum file size: 500KB
- Supported formats: JPEG, PNG

## Project Structure

```
mp3-vibe-artwork/
├── app.py                 # Flask application
├── processors/
│   ├── file_handler.py    # MP3 file processing
│   ├── artwork_processor.py # Image processing
│   └── musicbrainz_client.py # API integration
├── templates/
│   └── index.html         # Web interface
├── static/
│   ├── css/
│   └── js/
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Usage

1. Start the application using `python app.py`
2. Open your browser to `http://localhost:5001`
3. Select MP3 files or a folder containing MP3 files
4. Review and select artwork options when prompted
5. Download processed files from the output folder

## 🧪 **Testing**

The project includes comprehensive test suites for each phase:

**Core Component Tests:**
- **`test_file_handler.py`**: MP3 file validation and metadata extraction
- **`test_artwork_processor.py`**: Image processing and Traktor 3 compliance  
- **`test_file_operations.py`**: File operations and output management
- **`test_web_interface.py`**: Web interface and API endpoints

**Advanced Feature Tests:**
- **`test_musicbrainz_client.py`**: MusicBrainz API integration and artwork discovery
- **`test_phase5.py`**: End-to-end MusicBrainz integration testing
- **`test_phase6.py`**: User interaction features and artwork selection
- **`test_phase7.py`**: Error handling, progress tracking, and reliability testing

**Production Readiness Tests:**
- **`test_integration.py`**: Complete end-to-end workflow testing
- **`test_performance.py`**: Performance benchmarks and optimization verification
- **`test_phase8.py`**: Production deployment readiness and final validation

### Run Individual Test Suites
```bash
# Test core file processing
python test_file_handler.py
python test_artwork_processor.py
python test_file_operations.py

# Test web interface
python test_web_interface.py

# Test MusicBrainz integration  
python test_musicbrainz_client.py
python test_phase5.py

# Test user interaction features
python test_phase6.py

# Test error handling and reliability
python test_phase7.py

# Test production readiness
python test_integration.py
python test_performance.py
python test_phase8.py
```

### Run All Tests
```bash
# Run all test suites sequentially
python test_file_handler.py && \
python test_artwork_processor.py && \
python test_file_operations.py && \
python test_web_interface.py && \
python test_musicbrainz_client.py && \
python test_phase5.py && \
python test_phase6.py && \
python test_phase7.py && \
python test_integration.py && \
python test_performance.py && \
python test_phase8.py
```

**Total Test Coverage**: 200+ automated tests covering all functionality from basic file processing to production deployment readiness.

These tests should be run whenever making changes to verify that existing functionality hasn't been broken.

## 🚀 **Production Deployment**

The application is now production-ready with comprehensive configuration management:

### Quick Production Setup
```bash
# 1. Set environment variables
export SECRET_KEY="your-production-secret-key"
export FLASK_CONFIG="production"
export UPLOAD_FOLDER="/path/to/uploads"
export OUTPUT_FOLDER="/path/to/output"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run with WSGI server
gunicorn --bind 0.0.0.0:8000 wsgi:application
```

### Configuration Options
- **Development**: `FLASK_CONFIG=development` (debug enabled)
- **Testing**: `FLASK_CONFIG=testing` (testing mode)
- **Production**: `FLASK_CONFIG=production` (secure, optimized)

### Security Features
- ✅ Secure session cookies (HTTPS required in production)
- ✅ File upload size limits (100MB max)
- ✅ Directory traversal protection
- ✅ Error logging without debug info exposure
- ✅ Rate limiting for external API calls

### Monitoring & Logging
- ✅ Rotating log files (10MB max, 5 backups)
- ✅ Structured error categorization
- ✅ Performance metrics tracking
- ✅ Production health monitoring

## 🚀 **Project Status**

**Latest Version:** Phase 8 Complete - Production Ready Deployment  
**Current Status:** ✅ **COMPLETE PRODUCTION-READY MP3 ARTWORK MANAGER - ALL PHASES IMPLEMENTED**

### 📈 **Development Progress**
- ✅ **Phase 1**: Core MP3 Processing (File validation, metadata extraction, artwork processing)
- ✅ **Phase 2**: Artwork Standards Compliance (Traktor 3 optimization, format conversion) 
- ✅ **Phase 3**: Output Management (Folder structure, file organization, batch processing)
- ✅ **Phase 4**: Web Interface (File upload, progress tracking, result display)
- ✅ **Phase 5**: MusicBrainz Integration (Automatic artwork discovery and download)
- ✅ **Phase 6**: User Interaction Features (Artwork preview, selection, and comparison)
- ✅ **Phase 7**: Error Handling & Polish (Production-ready reliability and monitoring)
- ✅ **Phase 8**: Final Testing & Optimization (Integration testing, performance validation, deployment)

**🏁 PROJECT COMPLETE - READY FOR PRODUCTION DEPLOYMENT! 🎉**

## ✨ **Latest Updates**

### 🏁 **Phase 8: Final Testing & Optimization (COMPLETE!)** 
**Production deployment readiness with comprehensive testing:**

- **🧪 Integration Testing**: Complete end-to-end workflow verification from upload to download
- **⚡ Performance Optimization**: Handles 50MB+ files, memory-efficient batch processing, responsive UI
- **🔐 Production Configuration**: Secure deployment settings, environment-specific configs, WSGI ready
- **📚 Complete Documentation**: Step-by-step user guide, troubleshooting, FAQ, system requirements
- **🛡️ Security Hardening**: Production logging, secure cookies, file upload limits, error handling
- **📊 Monitoring**: Performance benchmarks, error tracking, production health monitoring

### 🛡️ **Phase 7: Error Handling & Polish** 
**Production-grade reliability and comprehensive error management:**

- **🔧 Comprehensive Error Handling**: Structured error categorization with severity levels (Critical, High, Medium, Low)
- **🔄 Intelligent Retry Logic**: Automatic retry for network and API errors with exponential backoff
- **📊 Advanced Progress Tracking**: Real-time progress with time estimation and current operation display
- **⏯️ Processing Controls**: Pause, resume, cancel, and retry operations for complete user control
- **📋 Detailed Error Logging**: Comprehensive error logs with export functionality for debugging
- **🎯 User-Friendly Messages**: Technical errors translated to clear, actionable user messages
- **🛑 Graceful Degradation**: Continue processing queue even when individual files fail
- **📈 Production Monitoring**: Error categorization and statistics for system health monitoring

### 🎨 **Phase 6: User Interaction Features** 
**Advanced artwork selection and preview capabilities:**

- **🖼️ Interactive Artwork Selection**: Browse and select from multiple artwork options found via MusicBrainz
- **👁️ Live Preview**: See exactly how artwork will look after Traktor 3 processing
- **📊 Before/After Comparison**: Side-by-side view showing original vs processed artwork with size/quality metrics
- **🎯 Smart Options**: Automatically sorted by relevance (front covers, approved images, higher resolution)
- **⏭️ Skip Option**: Choose to process files without artwork
- **💾 Session Memory**: Remembers your choices throughout the upload session
- **📱 Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices

### 🎵 **Phase 5: MusicBrainz Integration** 
**Automatic artwork discovery powered by the world's largest music database:**

- **🔍 Intelligent Search**: Automatically searches MusicBrainz when MP3 files lack artwork
- **🎨 Cover Art Archive**: Downloads high-quality artwork from official sources
- **⚡ Rate-Limited API**: Respects MusicBrainz API guidelines with automatic rate limiting
- **🎯 Smart Matching**: Uses metadata and filename parsing for accurate results
- **✅ Auto-Compliance**: Downloaded artwork is automatically processed to Traktor 3 specs
- **🔧 Configurable**: MusicBrainz integration can be enabled/disabled as needed

### 🔧 **Filename Preservation Fix**
**Critical improvement ensuring original filenames are never modified:**

- **Issue**: Previously `02-Inkswel & Colonel Red - Make Me Crazy (Potatohead People Remix) [Only Good Stuff].mp3`