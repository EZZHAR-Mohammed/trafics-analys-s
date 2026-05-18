# routers/video.py
"""
Endpoints du backend pour le traitement video.

Ce module gere le pipeline complet de traitement video :
- Upload de fichiers video (MP4, AVI, MOV, etc.)
- Traitement par flux optique (Lucas-Kanade et/ou Farneback)
- Gestion des jobs en memoire avec statut et resultats
- Analyse de frames individuelles avec visualisation
"""

import os
import shutil
import uuid
import base64
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional

from core.config import settings
from core.logger import logger
from schemas.models import ProcessVideoRequest, VideoProcessingResult
from services import video_processor

router = APIRouter()


@router.post("/upload", summary="Upload a video file")
async def upload_video(file: UploadFile = File(...)):
    """Upload un fichier video pour traitement.
    
    Formats acceptes : MP4, AVI, MOV, MKV, WebM
    Retourne :
    - Nom du fichier genere (UUID)
    - Chemin de stockage
    - Taille en MB
    - Metadonnees video (FPS, dimensions, duree)
    """
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}. Allowed: {allowed}")

    # Sauvegarde le fichier uploadé dans le dossier de réception.
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    dest = os.path.join(settings.UPLOAD_DIR, filename)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size_mb = os.path.getsize(dest) / (1024 * 1024)
    logger.info(f"📹 Uploaded: {filename} ({size_mb:.2f} MB)")

    # Recupere rapidement les metadonnees video (FPS, frames, dimensions, duree)
    cap = cv2.VideoCapture(dest)
    meta = {}
    if cap.isOpened():
        meta = {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration_sec": round(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1), 2),
        }
        cap.release()

    return {
        "filename": filename,
        "path": dest,
        "size_mb": round(size_mb, 2),
        "metadata": meta,
    }


@router.post("/process", summary="Process uploaded video with optical flow")
async def process_video(
    background_tasks: BackgroundTasks,
    filename: str = Query(..., description="Filename returned by /upload"),
    request: ProcessVideoRequest = ProcessVideoRequest(),
    run_async: bool = Query(False, description="Run in background (returns job_id immediately)"),
):
    """Lance le traitement d'une video uploadee avec les parametres specifies.

    Parametres importants :
    - method : lucas_kanade (sparse), farneback (dense), ou both
    - enable_tracking : activation du suivi des trajectoires
    - enable_alerts : activation de la detection d'anomalies
    - save_output : sauvegarde d'une video annotee en resultat
    - run_async : si True, retour immediat avec job_id; sinon, traitement synchrone
    """
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, f"File not found: {filename}")

    kwargs = dict(
        video_path=path,
        method=request.method.value,
        lk_params=request.lk_params.dict() if request.lk_params else None,
        fb_params=request.fb_params.dict() if request.fb_params else None,
        roi=request.roi.dict() if request.roi else None,
        enable_tracking=request.enable_tracking,
        enable_alerts=request.enable_alerts,
        speed_alert_threshold=request.speed_alert_threshold,
        motion_threshold=request.motion_threshold,
        save_output=request.save_output,
        max_frames=request.max_frames,
    )

    if run_async:
        # Lancer le traitement en arriere-plan et retourner immediatement un job_id.
        # Le client peut consulter l'etat via /jobs/{job_id}
        background_tasks.add_task(video_processor.process_video, **kwargs)
        return {"message": "Processing started in background", "check": "/api/v1/video/jobs"}

    # Traitement synchrone : l'appel attend la fin du traitement complet avant de retourner.
    result = video_processor.process_video(**kwargs)
    return result


@router.get("/jobs", summary="List all processing jobs")
async def list_jobs():
    """Liste tous les jobs de traitement soumis avec leur statut.
    
    Retourne chaque job avec son ID, statut (pending, processing, done, failed)
    et resultats si disponibles.
    """
    return video_processor.list_jobs()


@router.get("/jobs/{job_id}", summary="Get job status and result")
async def get_job(job_id: str):
    """Recupere le statut et le resultat d'un job de traitement.
    
    Retourne l'etat complet du job incluant :
    - Statut: pending, processing, done, ou failed
    - Resultats : trajectoires, alertes, statistiques de flux optique
    - Metadonnees : timestamps, parametres utilises
    """
    job = video_processor.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return job


@router.get("/frame/{filename}", summary="Analyze a single frame")
async def analyze_frame(
    filename: str,
    frame_number: int = Query(0, ge=0),
    method: str = Query("both", pattern="^(lucas_kanade|farneback|both)$"),
    return_image: bool = Query(True),
):
    """Extrait et analyse une frame specifique d'une video.
    
    Retourne :
    - Statistiques de flux optique (magnitude, nombre de points)
    - Images encodees en base64 avec les vecteurs de flux dessines
    - Temps de traitement pour chaque methode
    """
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_number >= total:
        cap.release()
        raise HTTPException(400, f"Frame {frame_number} out of range (total={total})")

    # Lire deux frames consecutives pour calculer le flux optique entre elles.
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(frame_number - 1, 0))
    ret1, frame1 = cap.read()
    ret2, frame2 = cap.read()
    cap.release()

    if not ret1 or not ret2:
        raise HTTPException(500, "Could not read frames")

    from services.optical_flow_engine import OpticalFlowEngine
    engine = OpticalFlowEngine()
    engine.process(frame1)  # premier calcul pour initialiser la mémoire du moteur
    results = engine.process(frame2, method=method)

    response = {"frame_number": frame_number, "method": method}

    if results.get("lk"):
        lk = results["lk"]
        response["lk"] = {
            "point_count": lk.point_count,
            "avg_magnitude": round(lk.avg_magnitude, 3),
            "max_magnitude": round(lk.max_magnitude, 3),
            "processing_ms": round(lk.processing_ms, 2),
        }
        if return_image:
            _, buf = cv2.imencode(".jpg", lk.frame_with_flow)
            response["lk_image_b64"] = base64.b64encode(buf).decode()

    if results.get("fb"):
        fb = results["fb"]
        response["fb"] = {
            "avg_magnitude": round(fb.avg_magnitude, 3),
            "max_magnitude": round(fb.max_magnitude, 3),
            "processing_ms": round(fb.processing_ms, 2),
        }
        if return_image:
            _, buf = cv2.imencode(".jpg", fb.hsv_visualization)
            response["fb_hsv_image_b64"] = base64.b64encode(buf).decode()
            _, buf = cv2.imencode(".jpg", fb.arrow_visualization)
            response["fb_arrow_image_b64"] = base64.b64encode(buf).decode()

    return response


@router.get("/frame/{filename}/annotated", summary="Get annotated frame with vectors as base64")
async def get_annotated_frame(
    filename: str,
    frame_number: int = Query(0, ge=0),
    method: str = Query("both", pattern="^(lucas_kanade|farneback|both)$"),
):
    """Extrait une frame et retourne l'image avec les vecteurs de flux optique dessines.
    
    Utile pour visualiser directement les mouvements detectes par Lucas-Kanade
    et/ou Farneback sur l'image.
    """
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_number >= total:
        cap.release()
        raise HTTPException(400, f"Frame {frame_number} out of range (total={total})")

    cap.set(cv2.CAP_PROP_POS_FRAMES, max(frame_number - 1, 0))
    ret1, frame1 = cap.read()
    ret2, frame2 = cap.read()
    cap.release()

    if not ret1 or not ret2:
        raise HTTPException(500, "Could not read frames")

    from services.optical_flow_engine import OpticalFlowEngine
    from services.tracker import VehicleTracker

    engine = OpticalFlowEngine()
    tracker = VehicleTracker()
    engine.process(frame1)
    results = engine.process(frame2, method=method)

    lk_res = results.get("lk")
    fb_res = results.get("fb")
    lk_frame = frame2.copy()
    fb_frame = frame2.copy()

    if lk_res:
        tracker.update(lk_res.good_new, lk_res.good_old)
        lk_frame = tracker.draw_tracks(lk_res.frame_with_flow)
        cv2.putText(lk_frame, "Lucas-Kanade (Sparse)", (10, lk_frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
    if fb_res:
        fb_frame = fb_res.arrow_visualization
        cv2.putText(fb_frame, "Farneback (Dense)", (10, fb_frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

    if method == "both" and lk_res is not None and fb_res is not None:
        annotated = np.hstack([lk_frame, fb_frame])
    elif method == "farneback" and fb_res is not None:
        annotated = fb_frame
    else:
        annotated = lk_frame

    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise HTTPException(500, "Failed to encode annotated frame")

    return {
        "filename": filename,
        "frame_number": frame_number,
        "method": method,
        "total_frames": total,
        "annotated_image_b64": base64.b64encode(buf).decode(),
    }


@router.delete("/upload/{filename}", summary="Delete uploaded video")
async def delete_video(filename: str):
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    os.remove(path)
    return {"message": f"Deleted {filename}"}
