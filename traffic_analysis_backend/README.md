# 🚗 Traffic Analysis Backend

Advanced REST API for vehicle movement analysis using **Lucas–Kanade** and **Farneback (Horn–Schunck)** optical flow.

---

## 🐍 Python Version — Which to Choose?

| Version | Status | Recommendation |
|---------|--------|---------------|
| Python 3.11 | ✅ **RECOMMENDED** | Best compatibility with OpenCV + NumPy + FastAPI |
| Python 3.12 | ⚠️ Works but some deps lag | Minor issues with some C extensions |
| Python 3.13 | ❌ NOT recommended | OpenCV wheels not yet stable for 3.13 |
| Python 3.10 | ✅ Works | Fine, but older |

> **Use Python 3.11** — it's the sweet spot for OpenCV 4.9, NumPy 1.26, and FastAPI 0.111.

---

## 📁 Project Structure

```
traffic_analysis_backend/
├── main.py                        # FastAPI app entry point
├── requirements.txt
├── .env                           # optional config overrides
│
├── core/
│   ├── config.py                  # settings & defaults
│   └── logger.py
│
├── schemas/
│   └── models.py                  # Pydantic request/response models
│
├── services/
│   ├── optical_flow_engine.py     # Lucas-Kanade + Farneback engines
│   ├── tracker.py                 # Multi-vehicle tracker
│   ├── alert_engine.py            # Anomaly & alert detection
│   └── video_processor.py        # Full processing pipeline
│
├── routers/
│   ├── video.py                   # /api/v1/video/*
│   ├── camera.py                  # /api/v1/camera/*
│   ├── optical_flow.py            # /api/v1/optical-flow/*
│   ├── tracking.py                # /api/v1/tracking/*
│   ├── analysis.py                # /api/v1/analysis/*
│   ├── alerts.py                  # /api/v1/alerts/*
│   └── export.py                  # /api/v1/export/*
│
├── uploads/                       # uploaded video files (auto-created)
└── outputs/                       # processed output videos (auto-created)
```

---

## ⚡ Quick Start

### 1. Install Python 3.11

**Windows:**
```bash
# Download from https://www.python.org/downloads/release/python-3119/
# Or use pyenv-win:
pyenv install 3.11.9
pyenv global 3.11.9
```

**macOS:**
```bash
brew install python@3.11
# or
pyenv install 3.11.9 && pyenv global 3.11.9
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

---

### 2. Create virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3.11 -m venv venv
source venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Run the server

```bash
# Development (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (multiple workers)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With explicit Python path (if multiple Python versions)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### 5. Open Swagger UI

```
http://localhost:8000/docs        ← Interactive Swagger
http://localhost:8000/redoc       ← ReDoc documentation
http://localhost:8000/health      ← Health check
```

---

## 🔬 Testing via Swagger — Step by Step

### Step 1: Upload a video
```
POST /api/v1/video/upload
→ Upload your .mp4 file
→ Copy the returned "filename" value
```

### Step 2: Process the video
```
POST /api/v1/video/process?filename=<your_filename>
Body:
{
  "method": "both",
  "enable_tracking": true,
  "enable_alerts": true,
  "save_output": true,
  "max_frames": 200
}
→ Copy the returned "job_id"
```

### Step 3: Explore results
```
GET /api/v1/analysis/{job_id}/summary          ← Overall stats
GET /api/v1/analysis/{job_id}/compare-methods  ← LK vs Farneback
GET /api/v1/tracking/{job_id}/tracks           ← Vehicle trajectories
GET /api/v1/alerts/{job_id}/all                ← All alerts
GET /api/v1/export/{job_id}/video              ← Download annotated video
GET /api/v1/export/{job_id}/csv/tracks         ← Download CSV
```

### Step 4: Test with two images (no video needed)
```
POST /api/v1/optical-flow/lucas-kanade/two-images
POST /api/v1/optical-flow/farneback/two-images
POST /api/v1/optical-flow/benchmark
```

### Step 5: Webcam (if available)
```
GET /api/v1/camera/list                   ← List cameras
GET /api/v1/camera/snapshot               ← Capture frame
POST /api/v1/camera/process-frames        ← Process 100 frames
GET /api/v1/camera/stream                 ← Open in browser for MJPEG stream
```

---

## 🌐 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/video/upload` | Upload video file |
| POST | `/api/v1/video/process` | Process video with optical flow |
| GET | `/api/v1/video/jobs` | List all jobs |
| GET | `/api/v1/video/jobs/{job_id}` | Get job status & result |
| GET | `/api/v1/video/frame/{filename}` | Analyze single frame |
| GET | `/api/v1/camera/list` | List available cameras |
| GET | `/api/v1/camera/snapshot` | Capture camera snapshot |
| POST | `/api/v1/camera/process-frames` | Process N frames from camera |
| GET | `/api/v1/camera/stream` | MJPEG live stream |
| GET | `/api/v1/camera/stream/status` | Stream statistics |
| POST | `/api/v1/optical-flow/lucas-kanade/two-images` | LK on 2 images |
| POST | `/api/v1/optical-flow/farneback/two-images` | Farneback on 2 images |
| POST | `/api/v1/optical-flow/benchmark` | Benchmark both methods |
| GET | `/api/v1/optical-flow/params/defaults` | Default parameters |
| GET | `/api/v1/tracking/{job_id}/tracks` | All vehicle tracks |
| GET | `/api/v1/tracking/{job_id}/fast-vehicles` | Fast vehicle filter |
| GET | `/api/v1/tracking/{job_id}/trajectory/{track_id}` | Single vehicle trajectory |
| GET | `/api/v1/analysis/{job_id}/summary` | Full analysis summary |
| GET | `/api/v1/analysis/{job_id}/compare-methods` | Method comparison |
| GET | `/api/v1/analysis/{job_id}/speed-distribution` | Speed histogram |
| GET | `/api/v1/analysis/{job_id}/frame-data` | Per-frame metrics |
| GET | `/api/v1/alerts/{job_id}/all` | All alerts |
| GET | `/api/v1/alerts/{job_id}/by-type` | Filter by type |
| GET | `/api/v1/alerts/{job_id}/timeline` | Alert timeline |
| GET | `/api/v1/export/{job_id}/json` | Export JSON |
| GET | `/api/v1/export/{job_id}/csv/tracks` | Export tracks CSV |
| GET | `/api/v1/export/{job_id}/csv/alerts` | Export alerts CSV |
| GET | `/api/v1/export/{job_id}/csv/frames` | Export frames CSV |
| GET | `/api/v1/export/{job_id}/video` | Download output video |

---

## ⚙️ Configuration (.env)

Create a `.env` file to override defaults:

```env
DEBUG=true
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs

# Lucas-Kanade
LK_MAX_CORNERS=300
LK_QUALITY_LEVEL=0.3
LK_MIN_DISTANCE=7.0

# Farneback
FB_PYR_SCALE=0.5
FB_LEVELS=3
FB_WINSIZE=15

# Tracking
TRACK_HISTORY_LEN=30
SPEED_ALERT_THRESHOLD=15.0

# Alerts
MOTION_THRESHOLD=2.0
```

---

## 🔥 Alert Types

| Type | Trigger |
|------|---------|
| `high_motion` | Average flow magnitude exceeds threshold |
| `fast_vehicle` | Tracked vehicle speed exceeds threshold |
| `motion_spike` | Flow magnitude suddenly triples |
| `sudden_stop` | Flow drops from high to near-zero |
| `congestion` | Many slow tracks simultaneously |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📦 Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t traffic-api .
docker run -p 8000:8000 traffic-api
```
