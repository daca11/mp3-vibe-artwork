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
# http://localhost:5000
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
2. Open your browser to `http://localhost:5000`
3. Select MP3 files or a folder containing MP3 files
4. Review and select artwork options when prompted
5. Download processed files from the output folder

### 🧪 Testing

The project includes comprehensive test suites for each phase:

```bash
# Test individual phases
python test_phase1.py      # Foundation & project setup
python test_phase2.py      # MP3 & image processing  
python test_phase3.py      # File operations
python test_phase4.py      # Web interface
python test_phase5.py      # MusicBrainz integration

# Test individual components
python test_file_handler.py       # MP3 file handling
python test_artwork_processor.py  # Image processing
python test_file_operations.py    # File operations & MusicBrainz
python test_web_interface.py      # Web interface & API
python test_musicbrainz_client.py # MusicBrainz API client
```

These tests should be run whenever making changes to verify that existing functionality hasn't been broken.

## Development Status

This project is currently in development. See `TODO.md` for implementation progress.

## 🎉 Project Status: COMPLETE - All Phases Implemented! 

**✅ Phase 1**: Flask Foundation & Project Setup - Complete  
**✅ Phase 2**: MP3 File Handling & Image Processing - Complete  
**✅ Phase 3**: File Operations & Processing Pipeline - Complete  
**✅ Phase 4**: Web Interface Integration - Complete  
**✅ Phase 5**: MusicBrainz Integration - Complete  

### 🔧 Latest Updates

**✅ PHASE 5: MUSICBRAINZ INTEGRATION COMPLETE! (Latest)**
- **🎵 Automatic Artwork Discovery**: When MP3 files have no embedded artwork, the application now automatically searches MusicBrainz and Cover Art Archive
- **🔍 Intelligent Search**: Uses ID3 metadata (artist, album, title) with filename parsing as fallback when metadata is missing
- **⚡ Rate-Limited API**: Respects MusicBrainz rate limits (1 request/second) with proper error handling
- **📐 Auto-Compliance**: Downloaded artwork is automatically processed to meet Traktor 3 specifications
- **🔧 Seamless Integration**: Works transparently within existing processing pipeline
- **⚙️ Configurable**: Can be enabled/disabled, maintains backward compatibility

**✅ FILENAME PRESERVATION FIXED**
- **Issue**: Application was sanitizing filenames, changing special characters
- **Example**: `02-Inkswel & Colonel Red - Make Me Crazy (Potatohead People Remix) [Only Good Stuff].mp3` → `02-Inkswel__Colonel_Red_-_Make_Me_Crazy_Potatohead_People_Remix_Only_Good_Stuff.mp3`
- **Solution**: Replaced `secure_filename()` with custom `safe_filename()` that preserves original filenames while preventing directory traversal attacks
- **Result**: Original MP3 filenames are now preserved exactly during upload and processing 