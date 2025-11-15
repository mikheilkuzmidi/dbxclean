# Dropbox Sorter

An intelligent file deduplication and organization tool for Dropbox that helps you clean up terabytes of data efficiently.

## Features

- **Duplicate File Detection**: Find exact duplicates based on content hash
- **Similar Image Detection**: Find similar images using perceptual hashing (not exact matches)
- **Image Quality Scoring**: Automatically identify the best quality version of similar images
- **File Renaming Suggestions**: Get intelligent suggestions for poorly named files
- **Cloud-Based Analysis**: Works with Dropbox cloud files without downloading everything to your laptop
- **Minimalistic UI**: Clean, intuitive interface inspired by Dropbox and Apple Photos
- **Safe Operations**: All deletions and renames require explicit user confirmation
- **Rate Limiting**: Respects Dropbox API limits with intelligent rate limiting

## Architecture

```
dropbox-sorter/
├── backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── analyzers/  # Duplicate, similar, quality, naming analyzers
│   │   ├── main.py     # FastAPI application
│   │   ├── dropbox_client.py  # Dropbox API wrapper
│   │   └── models.py   # Database models
│   └── requirements.txt
└── frontend/         # React frontend
    └── src/
        ├── pages/    # Dashboard, Duplicates, Similar, Files, Settings
        └── App.jsx
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Dropbox account with API access

## Quick Start

The fastest way to get started:

```bash
# Clone or download the repository
cd dropbox-sorter

# Run the installation script
./install.sh

# Or use make
make install

# Verify everything is working
./verify.sh
# Or: make verify

# Start the application
./start.sh
# Or: make start
```

For detailed setup instructions, see [SETUP.md](SETUP.md)

## Setup Instructions

### 1. Get Dropbox Access Token

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click "Create app"
3. Choose "Scoped access" and "Full Dropbox" access
4. Name your app (e.g., "Dropbox Sorter")
5. Go to the "Permissions" tab and enable:
   - `files.metadata.read`
   - `files.content.read`
   - `files.content.write`
6. Go to the "Settings" tab
7. Under "OAuth 2", click "Generate access token"
8. Copy the generated token (starts with `sl.`)

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Dropbox token
nano .env  # or use any text editor
```

Add your token to `.env`:
```env
DROPBOX_ACCESS_TOKEN=your_dropbox_token_here
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python -m app.main
```

Backend will run on `http://localhost:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Frontend will run on `http://localhost:3000`

### 5. Open in Browser

Navigate to `http://localhost:3000` and start using Dropbox Sorter!

## Usage Guide

### Initial Scan

1. Go to the Dashboard
2. Enter the path to scan (leave empty for root folder)
3. Click "Start Scan"
4. Wait for the scan to complete (progress bar will show status)

### Finding Duplicates

1. Navigate to "Duplicates" in the sidebar
2. Review duplicate groups
3. Files recommended to keep are highlighted in green
4. Select files to delete (non-recommended files are pre-selected)
5. Click "Delete Selected"
6. Confirm the action

### Finding Similar Images

1. Navigate to "Similar Images" in the sidebar
2. Review similar image groups
3. The best quality version is highlighted
4. Select lower quality versions to delete
5. Click "Delete Selected"
6. Confirm the action

### File Renaming

1. Navigate to "All Files"
2. Click "Get Naming Suggestions"
3. Review suggested names
4. Select files to rename
5. Click "Rename Selected"
6. Confirm the action

## Available Commands

The project includes convenient scripts and a Makefile:

```bash
# Installation
./install.sh          # Automated installation
make install          # Same as above

# Verification
./verify.sh           # Verify setup
make verify           # Same as above

# Running
./start.sh            # Start both backend and frontend
./stop.sh             # Stop all services
make start            # Start services
make stop             # Stop services

# Individual services
make backend          # Start backend only
make frontend         # Start frontend only

# Maintenance
make clean            # Clean build artifacts
make help             # Show all available commands
```

## Configuration

Edit `backend/.env` to configure:

```env
# Dropbox API
DROPBOX_ACCESS_TOKEN=your_token

# Database
DATABASE_URL=sqlite:///./dropbox_sorter.db

# Server
HOST=0.0.0.0
PORT=8000

# Analysis Settings
PERCEPTUAL_HASH_SIZE=8          # Hash size for image comparison
SIMILARITY_THRESHOLD=5           # Lower = more strict (0-64)
MAX_FILE_SIZE_MB=100            # Max image size to analyze
CACHE_EXPIRY_HOURS=24           # How long to cache file metadata
```

## API Rate Limiting

The application respects Dropbox API limits:
- Maximum 300 requests per minute (app uses conservative limit of 250)
- Automatic rate limiting and backoff
- Progress indicators for long operations

## Safety Features

- **No Automatic Deletions**: All deletions require explicit user confirmation
- **Preview Mode**: See what will be deleted before confirming
- **Recommended Files**: System highlights which files to keep
- **Error Handling**: Failed operations are reported without affecting successful ones
- **Database Caching**: File metadata is cached to minimize API calls

## How It Works

### Duplicate Detection
- Uses Dropbox content hash (SHA256-based)
- Groups files with identical content
- Recommends keeping files with better paths/names

### Similar Image Detection
- Downloads images or thumbnails for large files
- Computes perceptual hash (average hash)
- Compares images using Hamming distance
- Groups similar images together

### Quality Scoring
- **Resolution**: Higher megapixels = better
- **Sharpness**: Laplacian variance edge detection
- **Compression**: Bytes per pixel analysis
- **Aspect Ratio**: Penalizes extreme stretching
- Combined weighted score (0-100)

### File Naming
- Detects poorly named files (IMG_xxxx, Screenshot, etc.)
- Suggests names based on:
  - Folder context
  - Modification dates
  - File metadata
  - User patterns

## Troubleshooting

### Connection Error
- Verify your Dropbox access token in `.env`
- Check that all required permissions are enabled
- Ensure your token hasn't expired

### Slow Scanning
- Large folders take time (rate limiting)
- Consider scanning specific subfolders
- Disable image analysis for faster scans

### Out of Memory
- Reduce `MAX_FILE_SIZE_MB` in `.env`
- Scan smaller folders
- Clear database cache periodically

### Images Not Analyzed
- Check file size limits
- Verify image format is supported
- Check backend logs for errors

## Development

### Backend API Endpoints

- `GET /api/connection` - Check Dropbox connection
- `POST /api/scan` - Start folder scan
- `GET /api/jobs/{id}` - Get scan job status
- `GET /api/stats` - Get overall statistics
- `GET /api/duplicates` - Get duplicate groups
- `GET /api/similar` - Get similar image groups
- `GET /api/files` - List files
- `POST /api/delete` - Delete files (requires confirm=true)
- `POST /api/rename` - Rename files (requires confirm=true)

### Tech Stack

**Backend:**
- FastAPI - Modern async Python web framework
- SQLAlchemy - Database ORM
- Dropbox SDK - Official Dropbox API client
- Pillow - Image processing
- imagehash - Perceptual hashing

**Frontend:**
- React 18 - UI framework
- Vite - Build tool
- React Router - Routing
- Axios - HTTP client

## Contributing

This is a personal project. Feel free to fork and modify for your needs.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Dropbox API for cloud file access
- imagehash library for perceptual hashing
- Inspired by the need to clean up terabytes of accumulated digital clutter

## Support

For issues or questions, please open an issue on GitHub.

---

**Built with ❤️ for people tired of digital clutter**
