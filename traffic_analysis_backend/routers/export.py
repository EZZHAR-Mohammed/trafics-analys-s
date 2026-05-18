# routers/export.py
"""Endpoints d'export pour telecharger les resultats de l'analyse.

Ce module permet d'exporter les resultats de traitement video en plusieurs formats :
- JSON : resultat complet de l'analyse
- CSV : trajectoires, alertes et donnees frame par frame
- ZIP : archive complete avec tous les exports
- Video : telechargement de la video annotee finale
- Frames : telechargement de toutes les frames annotees en format image
"""

import os
import csv
import json
import io
import zipfile
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from services.video_processor import get_job
from core.config import settings

router = APIRouter()


@router.get("/{job_id}/json", summary="Export full result as JSON")
async def export_json(
    job_id: str,
    include_frame_data: bool = Query(False, description="Include per-frame data (large)"),
):
    """Telecharge le resultat complet du traitement en format JSON.
    
    Optionnellement inclut les donnees detaillees par frame (attention : fichier volumineux).
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    result = dict(job["result"])
    if not include_frame_data:
        result.pop("frame_results", None)

    content = json.dumps(result, indent=2)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=result_{job_id}.json"},
    )


@router.get("/{job_id}/csv/tracks", summary="Export vehicle tracks as CSV")
async def export_tracks_csv(job_id: str):
    """Exporte les trajectoires de tous les vehicules en format CSV.
    
    Inclut : ID de piste, vitesse, direction et detection de vehicule rapide.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    tracks = job["result"]["tracks"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["track_id", "speed_pixels_per_frame",
                                                 "direction_angle_deg", "is_fast"])
    writer.writeheader()
    for t in tracks:
        writer.writerow({
            "track_id": t["track_id"],
            "speed_pixels_per_frame": t["speed_pixels_per_frame"],
            "direction_angle_deg": t["direction_angle_deg"],
            "is_fast": t["is_fast"],
        })

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tracks_{job_id}.csv"},
    )


@router.get("/{job_id}/csv/alerts", summary="Export alerts as CSV")
async def export_alerts_csv(job_id: str):
    """Exporte toutes les alertes en format CSV.
    
    Inclut : index frame, timestamp, type d'alerte, magnitude et description.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    alerts = job["result"]["alerts"]
    output = io.StringIO()
    fieldnames = ["frame_index", "timestamp_sec", "alert_type", "magnitude", "description", "region"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for a in alerts:
        writer.writerow({
            "frame_index": a.get("frame_index"),
            "timestamp_sec": a.get("timestamp_sec"),
            "alert_type": a.get("alert_type"),
            "magnitude": a.get("magnitude"),
            "description": a.get("description"),
            "region": a.get("region") if a.get("region") is not None else "",
        })

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=alerts_{job_id}.csv"},
    )


@router.get("/{job_id}/csv/frames", summary="Export per-frame data as CSV")
async def export_frames_csv(job_id: str):
    """Exporte les metriques de flux optique pour chaque frame en format CSV.
    
    Utile pour l'analyse detaillee et les visualisations personnalisees.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    frames = job["result"]["frame_results"]
    if not frames:
        raise HTTPException(400, "No frame data")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(frames[0].keys()))
    writer.writeheader()
    writer.writerows(frames)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=frames_{job_id}.csv"},
    )


@router.get("/{job_id}/video", summary="Download the annotated output video")
async def download_video(job_id: str):
    """Download the processed annotated video file."""
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    url = job["result"].get("output_video_url")
    if not url:
        raise HTTPException(400, "No output video was saved for this job")

    # Strip leading slash
    path = url.lstrip("/")
    if not os.path.exists(path):
        raise HTTPException(404, f"Video file not found: {path}")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"traffic_result_{job_id}.mp4",
    )


@router.get("/{job_id}/frames-zip", summary="Download all annotated frames as ZIP")
async def download_frames_zip(job_id: str):
    """Zip and download all saved annotated frames for a completed job."""
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    frames_dir = os.path.join(settings.FRAMES_DIR, job_id)
    if not os.path.isdir(frames_dir):
        raise HTTPException(404, f"Frames directory not found: {frames_dir}")

    frame_files = sorted(
        f for f in os.listdir(frames_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not frame_files:
        raise HTTPException(400, "No frame images found for this job")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for frame_name in frame_files:
            abs_path = os.path.join(frames_dir, frame_name)
            zf.write(abs_path, arcname=frame_name)
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=frames_{job_id}.zip"},
    )
