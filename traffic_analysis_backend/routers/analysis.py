# routers/analysis.py
"""
Endpoints d'analyse et de comparaison pour les jobs traites.

Ce module fournit :
- Des resumes statistiques complets des traitements video
- Des comparaisons entre les methodes de flux optique
- Des analyses de distributions de vitesse et donnees de frames
"""

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from collections import defaultdict
from services.video_processor import get_job

router = APIRouter()


@router.get("/{job_id}/summary", summary="Full analysis summary for a job")
async def job_summary(job_id: str):
    """Retourne un resume statistique complet d'un job de traitement video.
    
    Inclut :
    - Nombre de frames traitees et FPS moyens
    - Statistiques detaillees pour chaque methode de flux optique
    - Evenements de mouvement et alertes detectees
    - Donnees de suivi des vehicules
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    result = job["result"]
    frames = result["frame_results"]

    lk_mags = [f["lk_avg_magnitude"] for f in frames if f.get("lk_avg_magnitude") is not None]
    fb_mags = [f["fb_avg_magnitude"] for f in frames if f.get("fb_avg_magnitude") is not None]
    proc_times = [f["processing_time_ms"] for f in frames]

    return {
        "job_id": job_id,
        "processed_frames": result["processed_frames"],
        "avg_processing_fps": result["avg_processing_fps"],
        "method": result["method"],
        "lk_statistics": {
            "avg_magnitude": round(float(np.mean(lk_mags)), 3) if lk_mags else None,
            "max_magnitude": round(float(np.max(lk_mags)), 3) if lk_mags else None,
            "std_magnitude": round(float(np.std(lk_mags)), 3) if lk_mags else None,
        } if lk_mags else None,
        "farneback_statistics": {
            "avg_magnitude": round(float(np.mean(fb_mags)), 3) if fb_mags else None,
            "max_magnitude": round(float(np.max(fb_mags)), 3) if fb_mags else None,
            "std_magnitude": round(float(np.std(fb_mags)), 3) if fb_mags else None,
        } if fb_mags else None,
        "processing_time": {
            "avg_ms": round(float(np.mean(proc_times)), 2),
            "min_ms": round(float(np.min(proc_times)), 2),
            "max_ms": round(float(np.max(proc_times)), 2),
        },
        "motion_events": sum(1 for f in frames if f["motion_detected"]),
        "alert_events": sum(1 for f in frames if f["alert_triggered"]),
        "total_alerts": result["stats"]["total_alerts"],
        "alert_summary": result["stats"]["alert_summary"],
        "tracking": result["stats"]["tracking"],
        "output_video_url": result.get("output_video_url"),
    }


@router.get("/{job_id}/compare-methods", summary="Side-by-side method comparison")
async def compare_methods(job_id: str):
    """Compare les performances de Lucas-Kanade vs Farneback pour un job.
    
    Retourne :
    - Vitesse (FPS) de chaque methode
    - Magnitudes de flux moyennes pour chaque methode
    - Types (sparse vs dense) et descriptions
    - Recommandations sur la meilleure methode selon le cas d'usage
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    result = job["result"]
    frames = result["frame_results"]
    stats = result["stats"]

    lk_fps = stats.get("lk_avg_fps")
    fb_fps = stats.get("fb_avg_fps")
    lk_mags = [f["lk_avg_magnitude"] for f in frames if f.get("lk_avg_magnitude") is not None]
    fb_mags = [f["fb_avg_magnitude"] for f in frames if f.get("fb_avg_magnitude") is not None]

    winner_speed = "N/A"
    if lk_fps and fb_fps:
        winner_speed = "lucas_kanade" if lk_fps > fb_fps else "farneback"

    comparison = {
        "job_id": job_id,
        "lucas_kanade": {
            "avg_fps": lk_fps,
            "avg_magnitude": round(float(np.mean(lk_mags)), 3) if lk_mags else None,
            "type": "sparse",
            "description": "Tracks specific feature points (corners). Fast, precise for individual vehicle tracking.",
        },
        "farneback": {
            "avg_fps": fb_fps,
            "avg_magnitude": round(float(np.mean(fb_mags)), 3) if fb_mags else None,
            "type": "dense",
            "description": "Computes flow at every pixel. Slower but gives complete motion field.",
        },
        "winner_speed": winner_speed,
        "recommendation": (
            "For real-time vehicle counting & speed estimation: Lucas-Kanade. "
            "For full motion field analysis & lane-level detection: Farneback."
        ),
        "frame_comparison_sample": [
            {
                "frame": f["frame_index"],
                "lk_mag": f.get("lk_avg_magnitude"),
                "fb_mag": f.get("fb_avg_magnitude"),
            }
            for f in frames[::max(1, len(frames) // 20)][:20]  # sample 20 frames
        ],
    }
    return comparison


@router.get("/{job_id}/speed-distribution", summary="Speed distribution of tracked vehicles")
async def speed_distribution(
    job_id: str,
    bins: int = Query(10, ge=3, le=50),
):
    """Calcule l'histogramme de distribution des vitesses des vehicules.
    
    Utile pour visualiser les plages de vitesse et identifier les anomalies.
    Retourne min, max, moyenne, et histogramme en intervalles.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    tracks = job["result"]["tracks"]
    if not tracks:
        return {"message": "No tracks found", "histogram": []}

    speeds = [t["speed_pixels_per_frame"] for t in tracks]
    hist, edges = np.histogram(speeds, bins=bins)

    return {
        "job_id": job_id,
        "track_count": len(speeds),
        "min_speed": round(float(np.min(speeds)), 2),
        "max_speed": round(float(np.max(speeds)), 2),
        "avg_speed": round(float(np.mean(speeds)), 2),
        "histogram": [
            {"range": f"{edges[i]:.1f}–{edges[i+1]:.1f}", "count": int(hist[i])}
            for i in range(len(hist))
        ],
    }


@router.get("/{job_id}/frame-data", summary="Get per-frame flow data")
async def frame_data(
    job_id: str,
    start: int = Query(0, ge=0),
    end: int = Query(100, ge=1),
):
    """Retourne les donnees de flux optique pour chaque frame (paginies).
    
    Permet une analyse detaillee frame par frame avec magnitudes
    et temps de traitement pour chaque methode.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    frames = job["result"]["frame_results"]
    return {
        "job_id": job_id,
        "total_frames": len(frames),
        "returned_frames": len(frames[start:end]),
        "data": frames[start:end],
    }
