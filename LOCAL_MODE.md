# Local Mode Guide

dbxclean now supports scanning and organizing files on your **local filesystem** without needing a Dropbox account or API access!

## Quick Start for Local Mode

### 1. Configure Local Mode

Edit `backend/.env` and set:

```env
STORAGE_MODE=local
LOCAL_ROOT=/path/to/your/files
```

**Examples:**
- `LOCAL_ROOT=/home/yourname/Documents` - Scan your Documents folder
- `LOCAL_ROOT=/home/yourname/Pictures` - Scan your Pictures folder
- Leave empty to use your home directory

### 2. Install and Run

```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start backend
python -m app.main
```

In another terminal:
```bash
# Start frontend
cd frontend
npm install
npm run dev
```

### 3. Use the App

Open `http://localhost:3000` in your browser. The interface is exactly the same - but now it works with your local files!

## Features in Local Mode

All the same powerful features work with local files:

- **Find duplicate files** based on content hash
- **Find similar images** using perceptual hashing
- **Quality scoring** to identify best versions
- **File naming suggestions** for poorly named files
- **Safe operations** - all deletions require confirmation

## How It Works

In local mode:
- The app scans files directly from your filesystem
- No downloads needed (files are already local!)
- Faster thumbnail generation
- Same database caching for quick re-scans
- All file operations (delete, rename) work on local files

## Comparison: Dropbox vs Local Mode

| Feature | Dropbox Mode | Local Mode |
|---------|--------------|------------|
| API Token Required | ✅ Yes | ❌ No |
| Internet Required | ✅ Yes | ❌ No |
| Rate Limiting | ✅ Yes (300/min) | ❌ No limits |
| Works Offline | ❌ No | ✅ Yes |
| Speed | Slower (downloads) | Faster (local) |
| File Access | Cloud only | Local only |

## Switching Between Modes

Just change the `STORAGE_MODE` setting in your `.env` file:

```env
# Use local filesystem
STORAGE_MODE=local
LOCAL_ROOT=/path/to/scan

# OR use Dropbox
STORAGE_MODE=dropbox
DROPBOX_ACCESS_TOKEN=your_token
```

Restart the backend server after changing modes.

## Safety Notes

Read [SAFETY.md](SAFETY.md) before deleting anything. It is the authority on
what this tool will and will not do to your files, and it is kept current with
the code; this guide is not.

The one thing worth repeating here: a local file this app deletes does not go to
a trash folder. Review before confirming, and try it on a copy first.

## Permissions

The app needs:
- **Read permission** - to scan and analyze files
- **Write permission** - to delete or rename files (only when confirmed)

Make sure the `LOCAL_ROOT` directory is readable and writable by the user running the app.

## Use Cases for Local Mode

Perfect for:
- Cleaning up your local photo library
- Organizing downloaded files
- Deduplicating local backups
- Finding similar images in your Pictures folder
- No internet connection required
- Privacy - files never leave your computer

## Troubleshooting

### "Root path does not exist"
- Check that `LOCAL_ROOT` exists
- Use absolute paths (e.g., `/home/user/Pictures` not `~/Pictures`)
- On Windows, use forward slashes: `C:/Users/YourName/Pictures`

### "Permission denied"
- Make sure you have read/write access to the directory
- On Linux/Mac, check permissions: `ls -la /path/to/directory`
- Try running with appropriate permissions

### Files not showing up
- Check that the path is correct
- Make sure the scan completed successfully
- Check the backend logs for errors
- Try a smaller directory first to test

## Example Configuration

Here's a complete `.env` file for local mode:

```env
# Use local filesystem mode
STORAGE_MODE=local

# Scan your Pictures folder
LOCAL_ROOT=/home/yourname/Pictures

# Database (default is fine)
DATABASE_URL=sqlite:///./dbxclean.db

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Analysis settings
PERCEPTUAL_HASH_SIZE=8
SIMILARITY_THRESHOLD=5
MAX_FILE_SIZE_MB=100
CACHE_EXPIRY_HOURS=24
```

## Performance Tips

- Start with a smaller directory to test
- Disable image analysis for faster initial scans
- The first scan takes longest; subsequent scans use cached data
- Large image files are automatically thumbnailed to save memory
- Database caching means re-scans are much faster

---

**Ready to clean up your local files?** Set `STORAGE_MODE=local` in your `.env` and start scanning!
