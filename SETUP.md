# Detailed Setup Guide

This guide will walk you through setting up Dropbox Sorter step by step.

## Prerequisites Check

Before starting, ensure you have:

```bash
# Check Python version (need 3.9+)
python --version

# Check Node.js version (need 18+)
node --version

# Check npm version
npm --version
```

If any are missing, install them first:
- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/

## Step 1: Clone or Download

If you haven't already:

```bash
git clone <repository-url>
cd dropbox-sorter
```

## Step 2: Dropbox API Setup

### Create Dropbox App

1. Visit https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose these options:
   - API: Scoped access
   - Access: Full Dropbox
   - Name: "Dropbox Sorter" (or your preferred name)
4. Click "Create app"

### Configure Permissions

1. Go to "Permissions" tab
2. Check these boxes:
   - `files.metadata.write`
   - `files.metadata.read`
   - `files.content.write`
   - `files.content.read`
3. Click "Submit" at the bottom

### Generate Access Token

1. Go to "Settings" tab
2. Scroll to "OAuth 2" section
3. Under "Generated access token", click "Generate"
4. Copy the token (it starts with `sl.`)
5. **Save this token securely** - you'll need it in the next step

## Step 3: Backend Configuration

```bash
cd backend

# Create Python virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env
```

Now edit the `.env` file:

```bash
# On macOS/Linux:
nano .env

# On Windows:
notepad .env
```

Update these values:

```env
DROPBOX_ACCESS_TOKEN=sl.your_actual_token_here

# Optional: customize these if needed
DATABASE_URL=sqlite:///./dropbox_sorter.db
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Analysis settings
PERCEPTUAL_HASH_SIZE=8
SIMILARITY_THRESHOLD=5
MAX_FILE_SIZE_MB=100
CACHE_EXPIRY_HOURS=24
```

Save and close the file.

## Step 4: Frontend Configuration

```bash
cd ../frontend

# Install Node.js dependencies
npm install

# This may take a few minutes
```

## Step 5: Test the Setup

### Test Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start the backend server
python -m app.main
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open a browser and visit: http://localhost:8000

You should see:
```json
{
  "name": "Dropbox Sorter API",
  "version": "1.0.0",
  "status": "running"
}
```

Leave this terminal running and open a new one.

### Test Frontend

```bash
cd frontend

# Start the frontend development server
npm run dev
```

You should see:
```
VITE v5.0.x  ready in xxx ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

## Step 6: Open the Application

1. Open your browser
2. Navigate to http://localhost:3000
3. You should see the Dropbox Sorter interface

If you see a connection error:
- Check that your Dropbox token is correct in `.env`
- Verify all permissions are enabled in Dropbox App Console
- Restart the backend server

## Step 7: Run Your First Scan

1. In the application, go to Dashboard
2. Leave the path empty (to scan root folder) or enter a specific folder path like `/Photos`
3. Click "Start Scan"
4. Wait for the scan to complete

The scan will:
- List all files in your Dropbox
- Analyze images for quality and similarity
- Detect duplicates
- Cache metadata in local database

**Note**: The first scan can take a while depending on:
- Number of files
- Number of images to analyze
- Your internet connection speed

## Common Issues and Solutions

### Issue: "Module not found" error in backend

**Solution:**
```bash
cd backend
pip install -r requirements.txt --force-reinstall
```

### Issue: "Cannot find module" error in frontend

**Solution:**
```bash
cd frontend
rm -rf node_modules
npm install
```

### Issue: "Address already in use" error

**Solution:**
- Backend: Change `PORT` in `.env` to 8001 or another port
- Frontend: Change port in `vite.config.js`

### Issue: Connection refused to backend

**Solution:**
- Make sure backend is running
- Check backend terminal for errors
- Verify port 8000 is not blocked by firewall

### Issue: Dropbox connection error

**Solution:**
1. Verify token in `.env` is correct (no extra spaces)
2. Check permissions in Dropbox App Console
3. Try generating a new token
4. Restart backend after changing token

### Issue: Images not being analyzed

**Solution:**
1. Check `MAX_FILE_SIZE_MB` in `.env` (increase if needed)
2. Verify image format is supported (jpg, png, gif, bmp, tiff, webp, heic)
3. Check backend logs for specific errors

### Issue: Scan is very slow

**Solution:**
This is normal! The application respects Dropbox rate limits:
- ~250 API calls per minute
- Image analysis takes time
- Large collections will take longer

Tips to speed up:
- Scan specific folders instead of root
- Disable image analysis for first scan (modify code to set `analyze_images=False`)
- Be patient - it's better to be safe than hit rate limits

## Production Deployment

For production use:

1. **Security**: Use environment variables instead of `.env` file
2. **Database**: Consider PostgreSQL instead of SQLite
3. **Backend**: Use gunicorn or similar WSGI server
4. **Frontend**: Build and serve static files
5. **HTTPS**: Use reverse proxy (nginx) with SSL
6. **Monitoring**: Add logging and error tracking

Example production setup:

```bash
# Backend
cd backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
# Serve the dist/ folder with nginx or similar
```

## Next Steps

Once setup is complete:

1. Read the main README.md for usage instructions
2. Run a test scan on a small folder
3. Explore duplicate detection
4. Try similar image detection
5. Test file renaming suggestions

## Getting Help

If you encounter issues:

1. Check the backend terminal for error messages
2. Check the browser console for frontend errors
3. Review this guide again
4. Check that all prerequisites are met
5. Open an issue on GitHub with:
   - Error messages
   - Steps to reproduce
   - Your environment (OS, Python version, Node version)

---

**Happy organizing!** 🎉
