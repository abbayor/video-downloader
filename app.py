import os
import re
import uuid
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory

import yt_dlp
import imageio_ffmpeg

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Portable ffmpeg binary bundled via imageio-ffmpeg — needed for MP3
# extraction, since Render's default Python environment has no system ffmpeg.
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# In-memory job store: {job_id: {"status": ..., "filename": ..., "error": ...}}
JOBS = {}

# How long a finished file is kept before we auto-delete it (seconds)
FILE_LIFETIME = 60 * 30  # 30 minutes

# Format string per requested quality. "hd" pulls the best available
# video+audio; "720p" caps resolution; "mp3" pulls audio only and is
# converted to mp3 via ffmpeg below.
FORMAT_MAP = {
    "hd": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    "mp3": "bestaudio/best",
}


def _cleanup_old_files():
    while True:
        now = time.time()
        for name in list(os.listdir(DOWNLOAD_DIR)):
            path = os.path.join(DOWNLOAD_DIR, name)
            try:
                if os.path.isfile(path) and now - os.path.getmtime(path) > FILE_LIFETIME:
                    os.remove(path)
            except OSError:
                pass
        time.sleep(300)


threading.Thread(target=_cleanup_old_files, daemon=True).start()


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-. ]", "_", name)
    return name[:150]


def _find_output_file(job_id: str) -> str | None:
    """Find whatever file yt-dlp (and ffmpeg postprocessing) produced for
    this job, regardless of final extension — mp3 conversion changes it."""
    for name in os.listdir(DOWNLOAD_DIR):
        if name.startswith(job_id + ".") and not name.endswith(".part"):
            return name
    return None


def _download_job(job_id: str, url: str, quality: str):
    JOBS[job_id] = {"status": "downloading", "filename": None, "display_name": None, "error": None}

    quality = quality if quality in FORMAT_MAP else "720p"

    # Use only the job_id in the actual file path on disk — avoids "filename
    # too long" errors from video captions/titles with lots of text or emoji.
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": FORMAT_MAP[quality],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH,
    }

    if quality == "mp3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            filename = _find_output_file(job_id)
            if not filename:
                raise RuntimeError("Download finished but the output file wasn't found.")

            ext = filename.rsplit(".", 1)[-1]
            raw_title = info.get("title") or "video"
            display_name = _safe_filename(raw_title)[:60] + f".{ext}"

            JOBS[job_id] = {
                "status": "done",
                "filename": filename,
                "display_name": display_name,
                "error": None,
            }
    except Exception as e:
        JOBS[job_id] = {"status": "error", "filename": None, "display_name": None, "error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    quality = (data or {}).get("quality", "720p").strip().lower()

    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Please provide a valid video URL."}), 400

    if quality not in FORMAT_MAP:
        quality = "720p"

    job_id = uuid.uuid4().hex[:12]
    thread = threading.Thread(target=_download_job, args=(job_id, url, quality), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job id"}), 404
    return jsonify(job)


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json(force=True)
    email = (data or {}).get("email", "").strip().lower()

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Please enter a valid email."}), 400

    subscribers_path = os.path.join(os.path.dirname(__file__), "subscribers.txt")
    try:
        with open(subscribers_path, "a") as f:
            f.write(email + "\n")
    except OSError:
        return jsonify({"error": "Could not save right now, try again."}), 500

    return jsonify({"ok": True})


@app.route("/api/file/<job_id>")
def get_file(job_id):
    job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "File not ready"}), 404
    return send_from_directory(
        DOWNLOAD_DIR,
        job["filename"],
        as_attachment=True,
        download_name=job.get("display_name") or job["filename"],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

