# Video Downloader — Deployment Guide (No Coding Required)

This is a small web app: a page where someone pastes a video URL and gets a
downloadable file back. It uses the open-source `yt-dlp` project to do the
actual fetching.

## Files in this project
- `app.py` — the backend (handles requests, runs yt-dlp, serves files)
- `templates/index.html` — the page people see and use
- `requirements.txt` — the list of libraries it needs installed
- `Procfile` — tells the hosting service how to start the app

## Easiest way to put this online: Render.com (free tier)

You don't need to touch a terminal for this.

1. Go to https://render.com and sign up (free).
2. Create a free GitHub account if you don't have one: https://github.com
3. Create a new GitHub repository (click "New repository"), name it
   `video-downloader`, and upload all the files from this folder using
   GitHub's "Add file → Upload files" button in your browser.
4. Back in Render, click **New +** → **Web Service**.
5. Connect your GitHub account and pick the `video-downloader` repo.
6. Render will ask for a few settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
7. Click **Create Web Service**. Render will build and deploy it — takes a
   few minutes. You'll get a live URL like `https://video-downloader-xxxx.onrender.com`
   that you can share with anyone.

## Alternative: Replit (even simpler, all in-browser)
1. Go to https://replit.com and sign up.
2. Create a new Repl → choose "Import from GitHub" (after uploading this
   project to GitHub as above), or "Python" template and upload these files
   manually via the file panel.
3. Click the green **Run** button. Replit installs dependencies and starts
   the app automatically.
4. Use the "Deploy" button in Replit to get a permanent public URL.

## Things to know before sharing this publicly
- Most video platforms (YouTube, Instagram, TikTok, etc.) prohibit
  downloading their content in their Terms of Service. This tool can be
  used against those terms, so treat it as something for personal /
  limited use rather than a public, branded product — see the earlier
  discussion on risk.
- The free tiers of Render/Replit are fine for testing but may be slow or
  sleep when not in use. If this gets real traffic, you'll eventually want
  a paid tier.
- Downloaded files are automatically deleted from the server after 30
  minutes to avoid filling up storage — you can change `FILE_LIFETIME` in
  `app.py` if you want that different.
