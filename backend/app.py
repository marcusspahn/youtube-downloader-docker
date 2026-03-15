import os
import subprocess
import threading
from flask import Flask, request, send_from_directory, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/downloads")
COOKIES_FILE = os.path.join(DOWNLOAD_DIR, "cookies.txt")
current_status = ""  # globaler Status

def convert_to_mp4_and_cleanup(input_file):
    base, ext = os.path.splitext(input_file)
    output_file = base + ".mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "copy", "-c:a", "aac", "-strict", "experimental",
            output_file
        ], check=True)
        if os.path.exists(output_file) and ext.lower() in [".webm", ".mkv"]:
            os.remove(input_file)
    except Exception as e:
        print(f"FFmpeg error: {e}")

@app.route("/")
def index():
    return f"""
    <!doctype html><meta charset='utf-8'>
    <h1>YT Downloader</h1>
    <form action="/download" method="post">
        <input type="text" name="url" placeholder="YouTube URL">
        <input type="submit" value="Download">
    </form>
    <div id="status" style="margin-top:10px;color:green;font-weight:bold;"></div>
    <script>
        setInterval(function(){{
            fetch('/status').then(r => r.json()).then(d => {{
                document.getElementById('status').innerText = d.status;
            }});
        }}, 1000);
    </script>
    <p><a href="/downloads">Alle fertigen Downloads ansehen</a></p>
    <h2>cookies.txt hochladen</h2>
    <form action="/upload_cookies" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <input type="submit" value="Upload">
    </form>
    """

@app.route("/status")
def status():
    return jsonify({"status": current_status})

@app.route("/download", methods=["POST"])
def download():
    global current_status
    url = request.form.get("url", "").strip()
    if not url:
        return redirect(url_for("index"))

    def worker():
        global current_status
        try:
            cmd = [
                "yt-dlp", "-o", os.path.join(DOWNLOAD_DIR, "%(title)s [%(id)s].%(ext)s"),
                "--newline", "--progress-template", "%(progress._percent_str)s | %(progress._eta_str)s ETA | %(progress._speed_str)s"
            ]
            if os.path.exists(COOKIES_FILE):
                cmd.extend(["--cookies", COOKIES_FILE])
            cmd.append(url)

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                current_status = line.strip()
            process.wait()

            current_status = "Konvertiere nach MP4..."
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.lower().endswith((".webm", ".mkv")):
                    convert_to_mp4_and_cleanup(os.path.join(DOWNLOAD_DIR, fname))
            current_status = "Fertig ✅"
        except Exception as e:
            current_status = f"Fehler: {e}"

    threading.Thread(target=worker, daemon=True).start()
    current_status = "Starte Download..."
    return redirect(url_for("index"))

@app.route("/upload_cookies", methods=["POST"])
def upload_cookies():
    if "file" not in request.files:
        return redirect(url_for("index"))
    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("index"))
    filename = secure_filename("cookies.txt")
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    file.save(save_path)
    return redirect(url_for("index"))

@app.route("/downloads")
def list_files_page():
    from urllib.parse import quote
    try:
        entries = []
        for name in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, name)
            if os.path.isfile(path) and name.lower().endswith(".mp4"):
                try:
                    size_mb = os.path.getsize(path) / 1048576.0
                    mtime   = os.path.getmtime(path)
                except Exception:
                    size_mb = 0.0
                    mtime   = 0.0
                entries.append((name, size_mb, mtime))
        entries.sort(key=lambda t: t[2], reverse=True)
    except Exception:
        entries = []

    items = []
    for name, size_mb, _ in entries:
        href = "/files/" + quote(name)
        items.append(f"<li><a href='{href}'>{name}</a> — {size_mb:.1f} MiB</li>")

    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Downloads</title>"
        "<h1>Downloads</h1>"
        "<ul>" + "\n".join(items) + "</ul>"
        "<p><a href='/'>Zurück</a></p>"
    )
    return html

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=False)

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=8099)
