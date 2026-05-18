# routers/camera.py
"""
Endpoints pour l'analyse de camera en direct (webcam/flux video live).

Ce module gere :
- Detection et enumeration des webcams disponibles
- Capture de snapshots 
- Traitement de N frames en temps reel avec statistiques
- Export des sessions enregistrees en CSV 
"""

import cv2
import base64
import time
import asyncio
import threading
import io
import csv
import json
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.logger import logger
from services.optical_flow_engine import OpticalFlowEngine
from services.tracker import VehicleTracker
from services.alert_engine import AlertEngine
from core.config import settings

router = APIRouter()

# État global du flux MJPEG (partage entre les clients)
_stream_state = {
    "active": False,
    "frame_count": 0,
    "fps": 0.0,
    "avg_magnitude": 0.0,
    "active_tracks": 0,
    "alert_count": 0,
    "method": "both",
}

_session_buffer = {
    "active": False,
    "started_at": None,
    "camera_index": 0,
    "method": "both",
    "frames": [],
    "alerts": [],
}


def _list_cameras(max_test: int = 5) -> list:
    """Detecte les indices des cameras disponibles sur le systeme.
    
    Teste les indices de camera de 0 a max_test-1 et retourne
    les cameras disponibles avec leurs resolutions.
    """
    available = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            available.append({"index": i, "width": w, "height": h})
            cap.release()
    return available


@router.get("/list", summary="List available cameras")
async def list_cameras():
    """Detecte et liste toutes les cameras connectees au systeme.
    
    Retourne pour chaque camera : index, largeur et hauteur en pixels.
    """
    cameras = _list_cameras()
    if not cameras:
        return {"cameras": [], "message": "No cameras detected"}
    return {"cameras": cameras}


@router.get("/snapshot", summary="Capture a single snapshot")
async def snapshot(
    camera_index: int = Query(0, ge=0),
    method: str = Query("both", pattern="^(lucas_kanade|farneback|both)$"),
    return_base64: bool = Query(True),
):
    """Capture une frame de la camera et applique l'analyse de flux optique.
    
    Retourne :
    - Image brute en base64
    - Statistiques de flux optique (magnitude, points, etc.)
    - Images annotees avec les vecteurs de mouvement
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise HTTPException(400, f"Camera {camera_index} not available")

    frames = []
    for _ in range(3):  # Capture quelques frames pour stabiliser la webcam
        ret, f = cap.read()
        if ret:
            frames.append(f)

    cap.release()

    if len(frames) < 2:
        raise HTTPException(500, "Could not capture frames")

    engine = OpticalFlowEngine()
    engine.process(frames[0])
    results = engine.process(frames[-1], method=method)

    response = {"camera_index": camera_index, "method": method, "captured": True}

    if return_base64:
        _, buf = cv2.imencode(".jpg", frames[-1])
        response["raw_frame_b64"] = base64.b64encode(buf).decode()

    if results.get("lk"):
        lk = results["lk"]
        response["lk_stats"] = {
            "point_count": lk.point_count,
            "avg_magnitude": round(lk.avg_magnitude, 3),
        }
        if return_base64:
            _, buf = cv2.imencode(".jpg", lk.frame_with_flow)
            response["lk_frame_b64"] = base64.b64encode(buf).decode()

    if results.get("fb"):
        fb = results["fb"]
        response["fb_stats"] = {
            "avg_magnitude": round(fb.avg_magnitude, 3),
            "max_magnitude": round(fb.max_magnitude, 3),
        }
        if return_base64:
            _, buf = cv2.imencode(".jpg", fb.arrow_visualization)
            response["fb_frame_b64"] = base64.b64encode(buf).decode()

    return response


@router.post("/process-frames", summary="Process N frames from camera")
async def process_camera_frames(
    camera_index: int = Query(0, ge=0),
    n_frames: int = Query(100, ge=10, le=1000),
    method: str = Query("both", pattern="^(lucas_kanade|farneback|both)$"),
    motion_threshold: float = Query(2.0, ge=0.1),
    speed_threshold: float = Query(15.0, ge=1.0),
    enable_tracking: bool = Query(True),
):
    """Capture et traite N frames de la webcam en temps reel.
    
    Applique l'analyse de flux optique, le suivi de trajectoires et la detection
    d'alertes. Retourne un resume statistique complet.
    Note: Pour un flux continu, utilisez /stream
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise HTTPException(400, f"Camera {camera_index} not available")

    # Initialiser les services d'analyse
    engine = OpticalFlowEngine()
    tracker = VehicleTracker()
    alert_eng = AlertEngine(motion_threshold=motion_threshold, speed_threshold=speed_threshold)

    lk_mags, fb_mags, times = [], [], []  # Accumulateurs de statistiques
    frame_idx = 0
    t_start = time.perf_counter()

    # Boucle de traitement des N frames
    while frame_idx < n_frames:
        ret, frame = cap.read()
        if not ret:
            break
        t0 = time.perf_counter()
        # Analyse de flux optique sur la frame
        results = engine.process(frame, method=method)
        lk_res = results.get("lk")
        fb_res = results.get("fb")

        # Mise a jour du suivi si active et Lucas-Kanade disponible
        if enable_tracking and lk_res:
            tracker.update(lk_res.good_new, lk_res.good_old)

        # Verification des alertes sur cette frame
        avg_mag = (lk_res.avg_magnitude if lk_res else 0) or (fb_res.avg_magnitude if fb_res else 0)
        alert_eng.check_flow(
            frame_idx=frame_idx,
            timestamp=frame_idx / 25.0,
            avg_magnitude=avg_mag,
            max_magnitude=lk_res.max_magnitude if lk_res else 0,
            active_tracks=tracker.get_stats()["active_tracks"],
            max_track_speed=tracker.get_stats()["max_speed"],
        )

        if lk_res:
            lk_mags.append(lk_res.avg_magnitude)
        if fb_res:
            fb_mags.append(fb_res.avg_magnitude)

        times.append((time.perf_counter() - t0) * 1000)
        frame_idx += 1

    cap.release()
    total_elapsed = time.perf_counter() - t_start

    import numpy as np
    return {
        "camera_index": camera_index,
        "frames_processed": frame_idx,
        "total_time_sec": round(total_elapsed, 2),
        "avg_fps": round(frame_idx / max(total_elapsed, 0.001), 2),
        "lk_avg_magnitude": round(float(np.mean(lk_mags)), 3) if lk_mags else None,
        "fb_avg_magnitude": round(float(np.mean(fb_mags)), 3) if fb_mags else None,
        "avg_processing_ms": round(float(np.mean(times)), 2),
        "alerts": [a.to_dict() for a in alert_eng.alerts],
        "tracking": tracker.get_stats(),
        "alert_summary": alert_eng.get_summary(),
    }


async def _mjpeg_generator(camera_index: int, method: str) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG stream with optical flow overlay."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return

    engine = OpticalFlowEngine()
    tracker = VehicleTracker()
    alert_eng = AlertEngine()

    frame_idx = 0
    t_fps = time.perf_counter()

    _stream_state["active"] = True
    _stream_state["method"] = method
    _session_buffer["active"] = True
    _session_buffer["started_at"] = time.time()
    _session_buffer["camera_index"] = camera_index
    _session_buffer["method"] = method
    _session_buffer["frames"] = []
    _session_buffer["alerts"] = []

    try:
        while _stream_state["active"]:
            ret, frame = cap.read()
            if not ret:
                break

            results = engine.process(frame, method=method)
            lk_res = results.get("lk")
            fb_res = results.get("fb")

            if lk_res:
                tracker.update(lk_res.good_new, lk_res.good_old)
                vis = tracker.draw_tracks(lk_res.frame_with_flow)
            else:
                vis = fb_res.arrow_visualization if fb_res else frame

            # FPS counter
            now = time.perf_counter()
            fps = 1.0 / max(now - t_fps, 0.001)
            t_fps = now

            avg_mag = (lk_res.avg_magnitude if lk_res else 0) or (fb_res.avg_magnitude if fb_res else 0)
            triggered = alert_eng.check_flow(frame_idx, frame_idx / 25.0, avg_mag, 0,
                                             tracker.get_stats()["active_tracks"],
                                             tracker.get_stats()["max_speed"])

            # Overlay HUD
            cv2.putText(vis, f"FPS: {fps:.1f}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f"Tracks: {tracker.get_stats()['active_tracks']}", (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(vis, f"Motion: {avg_mag:.2f}", (10, 85),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

            if triggered:
                cv2.rectangle(vis, (0, 0), (vis.shape[1], 35), (0, 0, 180), -1)
                cv2.putText(vis, f"ALERT: {triggered[0].alert_type}", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Update global state
            _stream_state["frame_count"] = frame_idx
            _stream_state["fps"] = round(fps, 1)
            _stream_state["avg_magnitude"] = round(avg_mag, 2)
            _stream_state["active_tracks"] = tracker.get_stats()["active_tracks"]
            _stream_state["alert_count"] = len(alert_eng.alerts)

            _session_buffer["frames"].append({
                "frame_index": frame_idx,
                "timestamp_sec": round(frame_idx / 25.0, 3),
                "camera_index": camera_index,
                "method": method,
                "fps": round(float(fps), 2),
                "magnitude": round(float(avg_mag), 6),
                "lk_avg_magnitude": round(float(lk_res.avg_magnitude), 6) if lk_res else "",
                "fb_avg_magnitude": round(float(fb_res.avg_magnitude), 6) if fb_res else "",
                "active_tracks": tracker.get_stats()["active_tracks"],
                "max_track_speed": round(float(tracker.get_stats()["max_speed"]), 6),
                "alert_triggered": bool(triggered),
            })
            if triggered:
                for alert in triggered:
                    _session_buffer["alerts"].append(alert.to_dict())

            _, buf = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

            frame_idx += 1
            await asyncio.sleep(0.001)
    finally:
        cap.release()
        _stream_state["active"] = False
        _session_buffer["active"] = False


@router.get("/stream", summary="Live MJPEG stream with optical flow overlay")
async def stream_camera(
    camera_index: int = Query(0, ge=0),
    method: str = Query("both", pattern="^(lucas_kanade|farneback|both)$"),
):
    """
    **MJPEG live stream** — open this URL in a browser `<img>` tag or video player.

    Overlay includes:
    - Optical flow vectors
    - Track trajectories
    - FPS / motion level HUD
    - Alert banner on anomalies
    """
    # Retourne un flux MJPEG exploitable dans un élément <img> HTML.
    return StreamingResponse(
        _mjpeg_generator(camera_index, method),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/stream/status", summary="Live stream status")
async def stream_status():
    """Get current camera stream statistics."""
    return _stream_state


@router.post("/stream/stop", summary="Stop the live stream")
async def stop_stream():
    """Stop the active camera stream."""
    _stream_state["active"] = False
    return {"message": "Stream stopped"}


@router.post("/save-session", summary="Save live camera session data as CSV/JSON")
async def save_session(
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """Export accumulated stream movement data from memory."""
    frames = _session_buffer.get("frames", [])
    if not frames:
        raise HTTPException(400, "No stream session data available. Start a stream first.")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    if format == "json":
        payload = {
            "camera_index": _session_buffer["camera_index"],
            "method": _session_buffer["method"],
            "started_at": _session_buffer["started_at"],
            "frames_count": len(frames),
            "frames": frames,
            "alerts": _session_buffer.get("alerts", []),
        }
        content = json.dumps(payload, indent=2)
        return StreamingResponse(
            io.StringIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=camera_session_{stamp}.json"},
        )

    csv_io = io.StringIO()
    writer = csv.DictWriter(csv_io, fieldnames=list(frames[0].keys()))
    writer.writeheader()
    writer.writerows(frames)
    csv_io.seek(0)
    return StreamingResponse(
        csv_io,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=camera_session_{stamp}.csv"},
    )
