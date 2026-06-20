"""
VidSave Pro - Backend Server
Uses yt-dlp to extract real video URLs and serve downloads.
Run: python server.py
Then open: http://localhost:5000
"""

import os, uuid, shutil, threading, tempfile, traceback
from flask import Flask, jsonify, request, send_file, send_from_directory
import yt_dlp

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR  = os.path.join(tempfile.gettempdir(), 'vidsave_dl')
os.makedirs(TEMP_DIR, exist_ok=True)

# ── Flask app ─────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

# ── Check ffmpeg (needed to merge video+audio for 1080p+ on YouTube) ───────
FFMPEG_PATH = shutil.which('ffmpeg')
if not FFMPEG_PATH:
    winget_base = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages')
    if os.path.isdir(winget_base):
        for item in os.listdir(winget_base):
            if item.startswith('Gyan.FFmpeg'):
                item_path = os.path.join(winget_base, item)
                found = False
                for root, dirs, files in os.walk(item_path):
                    if 'ffmpeg.exe' in files:
                        bin_dir = root
                        os.environ['PATH'] += os.pathsep + bin_dir
                        FFMPEG_PATH = shutil.which('ffmpeg')
                        if FFMPEG_PATH:
                            found = True
                            break
                if found:
                    break

FFMPEG = FFMPEG_PATH is not None
print(f"ffmpeg available: {FFMPEG} {'[YES]' if FFMPEG else '[NO - 1080p+ needs ffmpeg]'}")

# ── CORS headers for API routes ────────────────────────────────────────────
@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        res = app.make_response('')
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        res.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return res

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return r

# ══════════════════════════════════════════════════════════════════════════
#  Static file serving
# ══════════════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    safe = os.path.join(BASE_DIR, filename)
    if os.path.isfile(safe):
        return send_from_directory(BASE_DIR, filename)
    return jsonify({'error': 'Not found'}), 404

class MyLogger:
    def __init__(self):
        self.messages = []
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg):
        self.messages.append(msg)
    def error(self, msg):
        self.messages.append(msg)

# ── Check if Node.js is available for JS signature solving ──────────────────
NODE_AVAILABLE = shutil.which('node') is not None
print(f"Node.js available: {NODE_AVAILABLE} {'[YES]' if NODE_AVAILABLE else '[NO - will use fallback clients]'}")

def get_ydl_opts(custom_opts=None, use_cookies=True):
    logger = MyLogger()
    opts = {
        'quiet': True,
        'no_warnings': False,
        'noplaylist': True,
        'logger': logger,
    }

    # Use Node.js for JS signature solving if available, otherwise use
    # Android/TV clients that don't require JS decryption
    if NODE_AVAILABLE:
        opts['js_runtimes'] = 'node'
    else:
        # These clients use OAuth2/TV tokens and don't need JS solving
        # extractor_args format: each value must be a list of strings
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'tv_embedded', 'web_creator'],
            }
        }

    cookies_paths = [os.path.join(BASE_DIR, 'cookies.txt'), '/etc/secrets/cookies.txt']
    if use_cookies:
        for cookies_path in cookies_paths:
            if os.path.isfile(cookies_path):
                try:
                    with open(cookies_path, 'r', errors='ignore') as f:
                        content = f.read()
                    if 'youtube.com' in content or 'google.com' in content:
                        opts['cookiefile'] = cookies_path
                        print(f"Loaded cookies.txt for YouTube from {cookies_path}")
                        break
                    else:
                        print(f"cookies.txt at {cookies_path} found but ignored (no youtube/google cookies).")
                except Exception as e:
                    print(f"Error reading cookies.txt at {cookies_path}: {e}")
    if custom_opts:
        opts.update(custom_opts)
    return opts, logger

# ══════════════════════════════════════════════════════════════════════════
#  Debug Cookies API
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/debug/cookies')
def api_debug_cookies():
    results = {}
    cookies_paths = [os.path.join(BASE_DIR, 'cookies.txt'), '/etc/secrets/cookies.txt']
    for p in cookies_paths:
        exists = os.path.isfile(p)
        results[p] = {
            'exists': exists,
            'size': os.path.getsize(p) if exists else 0,
            'has_youtube': False,
            'preview': ''
        }
        if exists:
            try:
                with open(p, 'r', errors='ignore') as f:
                    content = f.read()
                results[p]['has_youtube'] = 'youtube.com' in content or 'google.com' in content
                results[p]['preview'] = content[:100].replace('\n', ' ')
            except Exception as e:
                results[p]['error'] = str(e)
    return jsonify(results)

# ══════════════════════════════════════════════════════════════════════════
#  Debug Node API
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/debug/node')
def api_debug_node():
    import subprocess
    results = {}
    try:
        res = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True)
        results['node'] = {'available': True, 'version': res.stdout.strip()}
    except Exception as e:
        results['node'] = {'available': False, 'error': str(e)}

    try:
        res = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True)
        results['ffmpeg'] = {'available': True, 'version': res.stdout.split('\n')[0]}
    except Exception as e:
        results['ffmpeg'] = {'available': False, 'error': str(e)}

    try:
        res = subprocess.run(['python', '-m', 'yt_dlp', '--version'], capture_output=True, text=True, check=True)
        results['yt_dlp'] = {'available': True, 'version': res.stdout.strip()}
    except Exception as e:
        results['yt_dlp'] = {'available': False, 'error': str(e)}
        
    return jsonify(results)

# ══════════════════════════════════════════════════════════════════════════
#  Quick test / verbose diagnostic endpoint
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/test')
def api_test():
    """Test YouTube extraction with a known short video and return full debug info."""
    test_url = request.args.get('url', 'https://www.youtube.com/watch?v=jNQXAC9IVRw')
    ydl_opts, logger = get_ydl_opts(use_cookies=False)
    ydl_opts['verbose'] = False  # keep quiet but capture errors

    result = {
        'node_available': NODE_AVAILABLE,
        'ffmpeg_available': FFMPEG,
        'ydl_opts_keys': list(ydl_opts.keys()),
        'url': test_url,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        result['success'] = True
        result['title'] = info.get('title')
        result['formats_count'] = len(info.get('formats', []))
        result['logger_messages'] = logger.messages
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        result['logger_messages'] = logger.messages

    return jsonify(result)

# ══════════════════════════════════════════════════════════════════════════
#  GET /api/info?url=...
#  Returns video metadata + list of available formats
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/info')
def api_info():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    nocookies = request.args.get('nocookies', 'false').lower() == 'true'
    ydl_opts, logger = get_ydl_opts(use_cookies=not nocookies)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        logs = " | Logs: " + "; ".join(logger.messages) if logger.messages else ""
        if 'Private video' in msg:
            return jsonify({'error': 'This video is private and cannot be downloaded.'}), 400
        if 'age' in msg.lower():
            return jsonify({'error': 'This video is age-restricted. Please try another video.'}), 400
        if 'Requested format is not available' in msg or 'Video unavailable' in msg:
            return jsonify({'error': f'Video formats are encrypted or unavailable. Make sure Node.js is installed on the server.{logs}'}), 400
        return jsonify({'error': f'Could not fetch video: {_short(msg)}{logs}'}), 400
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] api_info exception: {tb}")
        return jsonify({'error': _short(str(e)), 'traceback': tb[:500]}), 500

    formats_raw = info.get('formats', [])

    # ── Build video format list ────────────────────────────────────────────
    by_height = {}
    for f in formats_raw:
        h = f.get('height')
        if not h:
            continue
        vcodec = f.get('vcodec', 'none') or 'none'
        acodec = f.get('acodec', 'none') or 'none'
        has_v = vcodec not in ('none', '')
        has_a = acodec not in ('none', '')

        if not has_v:
            continue  # Skip audio-only streams in video section

        is_prog = has_v and has_a
        is_video_only = has_v and not has_a

        if h not in by_height:
            by_height[h] = {'prog': None, 'video_only': None}

        if is_prog:
            current_prog = by_height[h]['prog']
            if not current_prog or (f.get('tbr') or 0) > (current_prog.get('tbr') or 0):
                by_height[h]['prog'] = f
        elif is_video_only:
            current_vo = by_height[h]['video_only']
            if not current_vo or (f.get('tbr') or 0) > (current_vo.get('tbr') or 0):
                by_height[h]['video_only'] = f

    video_fmts = []
    # Add a fallback format that works 100% of the time without merging
    video_fmts.append({
        'format_id':    'best[ext=mp4]/best',
        'label':        'Best Quality (No App Needed)',
        'quality':      'best_no_ffmpeg',
        'ext':          'MP4',
        'badge':        'FAST',
        'size':         'Varies',
        'is_audio':     False,
        'needs_ffmpeg': False,
        'available':    True,
    })

    for h in sorted(by_height.keys(), reverse=True):
        prog = by_height[h]['prog']
        video_only = by_height[h]['video_only']

        if not prog and not video_only:
            continue

        if   h >= 2160: badge, lbl = '4K',  f'{h}p Ultra HD'
        elif h >= 1440: badge, lbl = '2K',  f'{h}p 2K'
        elif h >= 1080: badge, lbl = 'FHD', f'{h}p Full HD'
        elif h >= 720:  badge, lbl = 'HD',  f'{h}p HD'
        else:           badge, lbl = f'{h}p', f'{h}p'

        # If we have a progressive stream and either:
        # 1. ffmpeg is NOT available (so we must use progressive to work)
        # 2. or there is no video_only stream of this resolution
        if prog and (not FFMPEG or not video_only):
            fmt_id = prog['format_id']
            needs_ffmpeg = False
            fs = prog.get('filesize') or prog.get('filesize_approx')
        else:
            fmt_id = f'bestvideo[height={h}]+bestaudio/best[height<={h}]'
            needs_ffmpeg = True
            fs = (video_only.get('filesize') or video_only.get('filesize_approx')) if video_only else None

        video_fmts.append({
            'format_id':    fmt_id,
            'label':        lbl,
            'quality':      f'{h}p',
            'ext':          'MP4',
            'badge':        badge,
            'size':         _fmt_size(fs),
            'is_audio':     False,
            'needs_ffmpeg': needs_ffmpeg,
            'available':    (not needs_ffmpeg) or FFMPEG,
        })

    # ── Audio-only formats ─────────────────────────────────────────────────
    audio_fmts = [
        {
            'format_id': 'bestaudio[ext=m4a]/bestaudio/best',
            'label':     'MP3 Best Quality',
            'quality':   'audio',
            'ext':       'MP3',
            'badge':     'MP3',
            'size':      '~5–30 MB',
            'is_audio':  True,
            'needs_ffmpeg': not FFMPEG,
            'available': True,
        },
        {
            'format_id': 'worstaudio/worst',
            'label':     'MP3 Low Quality',
            'quality':   'audio_low',
            'ext':       'MP3',
            'badge':     'MP3',
            'size':      '~2–8 MB',
            'is_audio':  True,
            'needs_ffmpeg': not FFMPEG,
            'available': True,
        },
    ]

    # ── Thumbnail ──────────────────────────────────────────────────────────
    thumb = info.get('thumbnail', '')
    thumbs = info.get('thumbnails', [])
    if thumbs:
        thumb = max(thumbs, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0)).get('url', thumb)

    return jsonify({
        'title':    info.get('title', 'Video'),
        'channel':  info.get('uploader') or info.get('channel') or '',
        'duration': _fmt_dur(info.get('duration') or 0),
        'views':    _fmt_views(info.get('view_count')),
        'thumbnail': thumb,
        'formats':  video_fmts + audio_fmts,
    })


import json

def _get_task_path(task_id):
    return os.path.join(TEMP_DIR, f'task_{task_id}.json')

def _save_task(task_id, data):
    try:
        path = _get_task_path(task_id)
        # Atomic write to avoid race conditions during polling
        temp_fd, temp_path = tempfile.mkstemp(dir=TEMP_DIR, prefix=f'task_{task_id}_', suffix='.tmp')
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(data, f)
        os.replace(temp_path, path)
    except Exception as e:
        print(f"Error saving task {task_id}: {e}")

def _load_task(task_id):
    try:
        path = _get_task_path(task_id)
        if os.path.isfile(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading task {task_id}: {e}")
    return None

def make_progress_hook(task_id):
    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            if total > 0:
                percent = int(downloaded / total * 100)
            else:
                percent = 0

            speed = d.get('_speed_str') or 'N/A'
            eta = d.get('_eta_str') or 'N/A'

            task = _load_task(task_id) or {}
            task.update({
                'status': 'downloading',
                'progress': percent,
                'speed': speed.strip(),
                'eta': eta.strip()
            })
            _save_task(task_id, task)
        elif d['status'] == 'finished':
            task = _load_task(task_id) or {}
            task.update({
                'status': 'processing',
                'progress': 100
            })
            _save_task(task_id, task)
    return hook

def run_download_thread(task_id, url, format_id, is_audio):
    uid          = str(uuid.uuid4())[:10]
    out_template = os.path.join(TEMP_DIR, f'{uid}.%(ext)s')

    pps = []
    if is_audio and FFMPEG:
        pps = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]

    ydl_opts, _ = get_ydl_opts({
        'format':              format_id,
        'outtmpl':             out_template,
        'postprocessors':      pps,
        'merge_output_format': 'mp4' if not is_audio else None,
        'progress_hooks':      [make_progress_hook(task_id)],
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            task = _load_task(task_id) or {}
            task['title'] = title
            _save_task(task_id, task)

        # Find the downloaded file
        dl_file = None
        for fname in os.listdir(TEMP_DIR):
            if fname.startswith(uid):
                dl_file = os.path.join(TEMP_DIR, fname)
                break

        if not dl_file or not os.path.isfile(dl_file):
            task = _load_task(task_id) or {}
            task.update({
                'status': 'failed',
                'error': 'File not found after download. Please try a different quality.'
            })
            _save_task(task_id, task)
            return

        task = _load_task(task_id) or {}
        task.update({
            'status': 'completed',
            'file_path': dl_file,
            'progress': 100
        })
        _save_task(task_id, task)
    except Exception as e:
        task = _load_task(task_id) or {}
        task.update({
            'status': 'failed',
            'error': str(e)
        })
        _save_task(task_id, task)

@app.route('/api/download/start')
def api_download_start():
    url       = request.args.get('url', '').strip()
    format_id = request.args.get('format_id', 'best')
    is_audio  = request.args.get('audio', 'false').lower() == 'true'

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    task_id = str(uuid.uuid4())
    task = {
        'status': 'starting',
        'progress': 0,
        'speed': 'N/A',
        'eta': 'N/A',
        'title': 'Video',
        'file_path': None,
        'error': None
    }
    _save_task(task_id, task)

    t = threading.Thread(target=run_download_thread, args=(task_id, url, format_id, is_audio))
    t.daemon = True
    t.start()

    return jsonify({'task_id': task_id})

@app.route('/api/download/status')
def api_download_status():
    task_id = request.args.get('task_id', '')
    task = _load_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)

@app.route('/api/download/file')
def api_download_file():
    task_id = request.args.get('task_id', '')
    task = _load_task(task_id)
    if not task or task.get('status') != 'completed':
        return jsonify({'error': 'File not ready or task not found'}), 404

    dl_file = task['file_path']
    if not dl_file or not os.path.isfile(dl_file):
        return jsonify({'error': 'File not found on disk'}), 404

    title = task.get('title', 'video')
    ext   = os.path.splitext(dl_file)[1].lstrip('.')
    safe_title  = ''.join(c for c in title if c.isalnum() or c in ' _-()').strip()[:60]
    dl_name     = f'{safe_title}.{ext}'
    mime        = 'audio/mpeg' if ext == 'mp3' else ('audio/mp4' if ext == 'm4a' else 'video/mp4')

    # Schedule cleanup after 5 minutes
    def _cleanup():
        try:
            if os.path.isfile(dl_file):
                os.remove(dl_file)
            path = _get_task_path(task_id)
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
    threading.Timer(300, _cleanup).start()

    return send_file(dl_file, as_attachment=True, download_name=dl_name, mimetype=mime)


# ══════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════
def _fmt_dur(s):
    s = int(s or 0)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f'{h}:{m:02d}:{sec:02d}' if h else f'{m}:{sec:02d}'

def _fmt_size(b):
    if not b: return 'Unknown'
    for u in ('B', 'KB', 'MB', 'GB'):
        if b < 1024: return f'{b:.1f} {u}'
        b /= 1024
    return f'{b:.1f} GB'

def _fmt_views(v):
    if not v: return ''
    if v >= 1_000_000: return f'{v/1_000_000:.1f}M views'
    if v >= 1_000:     return f'{v/1_000:.0f}K views'
    return f'{v} views'

def _short(s, n=250):
    return s[:n] + ('…' if len(s) > n else '')


# ══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print('\n' + '='*55)
    print('  VidSave Pro  --  Real Video Downloader Backend')
    print('='*55)
    print(f'  Open in browser: http://localhost:5000')
    print(f'  Serving files from: {BASE_DIR}')
    print(f'  Temp downloads:     {TEMP_DIR}')
    print(f'  ffmpeg:             {"[YES] Found" if FFMPEG else "[NO] Not found (720p max without it)"}')
    print('='*55 + '\n')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
