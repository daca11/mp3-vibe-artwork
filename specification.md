# MP3 Artwork Manager - Software Specification

## 1. Project Overview

### 1.1 Project Name
MP3 Artwork Manager for Traktor 3

### 1.2 Purpose
A web-based application that analyzes MP3 files, resizes embedded ID3 artwork to meet Traktor 3 specifications, and fetches missing artwork using the MusicBrainz API.

### 1.3 Target Users
DJs and music enthusiasts who use Traktor 3 and need their MP3 collection to have properly sized artwork.

## 2. Functional Requirements

### 2.1 Core Features

#### 2.1.1 File Processing
- **Input Support**: Process single MP3 files or entire folders
- **File Scope**: Process files only in the selected folder (no subdirectory recursion)
- **File Size**: No file size limits imposed by the application
- **Output**: Create processed files in a separate output folder (original files remain unmodified)
- **Filename Preservation**: Original MP3 filenames must be preserved exactly - no sanitization, cleaning, or modification of filenames during processing

#### 2.1.2 Artwork Processing
- **Target Specifications**: 
  - Maximum dimensions: 500x500 pixels
  - Maximum file size: 500KB
  - Supported formats: JPEG, PNG
- **Processing Logic**:
  - If artwork exists and meets specifications: copy file to output folder unchanged
  - If artwork exists but doesn't meet specifications: resize and optimize
  - If no artwork exists: search MusicBrainz API and embed found artwork

#### 2.1.3 MusicBrainz Integration
- **Primary Matching**: Use existing ID3 metadata (artist, album, title) to search for artwork
- **Fallback Matching**: Parse filename to extract artist and title when ID3 metadata is incomplete
- **Multiple Results Handling**: Present user with options when multiple artwork candidates are found
- **Rate Limiting**: Respect MusicBrainz API rate limit of 1 request per second

#### 2.1.4 User Interface Features
- **File Selection**: Web interface for selecting single files or folders
- **Processing Queue**: Display current processing status and queue
- **Artwork Preview**: Show artwork before applying changes
- **Manual Selection**: Allow user to choose from multiple artwork options
- **Progress Tracking**: Real-time status updates during processing
- **Persistent Notifications**: Status messages and alerts remain visible until manually dismissed by user
  - No auto-dismissal of notifications
  - Manual dismiss button (✕) for each notification
  - Consistent notification behavior across all application functions

### 2.2 User Workflow

1. **File Selection**: User selects MP3 files or folder via web interface
2. **Queue Building**: Application scans and builds processing queue
3. **Processing**: For each file:
   - Analyze current artwork
   - If artwork missing or invalid, search MusicBrainz
   - If multiple options found, present to user for selection
   - Process and save to output folder
4. **Completion**: Display summary of processed files

## 3. Technical Requirements

### 3.1 Technology Stack
- **Backend**: Python with Flask (lightweight web framework)
- **Audio Processing**: mutagen (ID3 tag handling)
- **Image Processing**: Pillow (PIL) (resize, format conversion, optimization)
- **API Integration**: musicbrainzngs (MusicBrainz API client)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)

### 3.2 Architecture

#### 3.2.1 Backend Components
- **Flask Application**: Main web server and API endpoints
- **File Handler**: MP3 file scanning and processing
- **Artwork Processor**: Image resizing and optimization
- **MusicBrainz Client**: API interaction and metadata matching
- **Queue Manager**: Processing queue and status tracking

#### 3.2.2 API Endpoints
- `GET /` - Main application interface
- `POST /upload` - File/folder selection
- `GET /queue` - Processing queue status
- `POST /process` - Start processing queue
- `GET /artwork-options/<file_id>` - Get artwork options for user selection
- `POST /select-artwork` - User artwork selection
- `GET /download/<file_id>` - Download processed file

### 3.3 Data Flow

```
1. User uploads files → Queue created
2. For each file:
   a. Extract ID3 metadata
   b. Check existing artwork
   c. If artwork missing/invalid:
      - Search MusicBrainz API
      - Present options to user (if multiple)
      - Download selected artwork
   d. Process artwork (resize/optimize)
   e. Embed in MP3 copy
   f. Save to output folder
```

## 4. Non-Functional Requirements

### 4.1 Performance
- **Processing Speed**: Handle files efficiently without UI blocking
- **Memory Usage**: Stream process large files to avoid memory issues
- **API Compliance**: Maintain 1 request/second limit to MusicBrainz

### 4.2 Reliability
- **Error Handling**: Graceful handling of corrupted files, API failures, and network issues
- **Data Safety**: Never modify original files
- **Logging**: Basic error reporting to user interface

### 4.3 Usability
- **Interface**: Clean, intuitive web interface
- **Feedback**: Clear progress indicators and persistent error messages
  - All notifications remain visible until manually dismissed
  - Each notification includes a dismiss button for user control
  - No automatic timeout or hiding of important messages
- **Browser Support**: Modern web browsers (Chrome, Firefox, Safari, Edge)

## 5. Error Handling

### 5.1 File Processing Errors
- **Corrupted Files**: Display error message, continue with next file
- **Unsupported Files**: Skip non-MP3 files with notification
- **Write Permissions**: Alert user if output folder is not writable

### 5.2 API Errors
- **MusicBrainz Unavailable**: Display error message and stop processing queue
- **Rate Limiting**: Built-in delay to respect API limits
- **No Results Found**: Show warning message and continue processing without artwork embedding

### 5.3 User Input Errors
- **Invalid File Selection**: Clear error messaging
- **Network Issues**: Timeout handling and user notification

## 6. Implementation Details

### 6.1 Artwork Specifications
```python
ARTWORK_SPECS = {
    'max_width': 500,
    'max_height': 500,
    'max_file_size': 500 * 1024,  # 500KB
    'formats': ['JPEG', 'PNG']
}
```

### 6.2 MusicBrainz Search Strategy
1. **Primary**: Search using `artist + album + title` from ID3 tags
2. **Fallback**: Parse filename for `artist - title` pattern
3. **Query Format**: Use MusicBrainz query syntax for best matches

### 6.3 File Organization
```
project/
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
└── requirements.txt       # Python dependencies
```

## 7. Dependencies

### 7.1 Python Packages
```
Flask>=2.0.0
mutagen>=1.45.0
Pillow>=9.0.0
musicbrainzngs>=0.7.0
requests>=2.25.0
```

### 7.2 System Requirements
- Python 3.8+
- Modern web browser
- Internet connection for MusicBrainz API

## 8. Deployment

### 8.1 Development
- Run locally using Flask development server
- Access via `http://localhost:5001`

### 8.2 Production Considerations
- Use production WSGI server (Gunicorn, uWSGI)
- Configure proper error logging
- Set up output folder with appropriate permissions

## 9. Future Enhancements (Out of Scope)

- Batch processing automation
- Multiple output format support
- Undo/backup functionality
- Advanced metadata editing
- Integration with other music databases
- Support for other audio formats

## 10. Success Criteria

The application will be considered successful when:
1. It can process MP3 files and resize artwork to Traktor 3 specifications
2. It can fetch missing artwork from MusicBrainz API
3. It provides a user-friendly web interface
4. It handles errors gracefully without data loss
5. It respects MusicBrainz API rate limits and terms of service

---

**Document Version**: 1.0  
**Last Updated**: August 2025  
**Status**: Ready for Implementation