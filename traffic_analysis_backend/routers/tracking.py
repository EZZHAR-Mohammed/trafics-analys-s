# routers/tracking.py
"""
Endpoints pour l'accès aux données de suivi des véhicules.

Ce module permet de consulter les trajectoires des véhicules détectés
dans les vidéos traitées, les véhicules rapides, et les trajectoires détaillées.
"""

from fastapi import APIRouter, HTTPException, Query
from services.video_processor import get_job

router = APIRouter()


@router.get("/{job_id}/tracks", summary="Get all vehicle tracks for a processed job")
async def get_tracks(job_id: str):
    """Recupere toutes les trajectoires de vehicules d'un job traite.
    
    Retourne :
    - job_id : identifiant du job
    - tracks : liste complete des trajectoires detectees
    - stats : statistiques du suivi (nombre de pistes, vitesse max, etc.)
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done":
        raise HTTPException(400, f"Job status: {job['status']} (must be 'done')")
    return {
        "job_id": job_id,
        "tracks": job["result"]["tracks"],
        "stats": job["result"]["stats"]["tracking"],
    }


@router.get("/{job_id}/fast-vehicles", summary="Get only fast vehicle tracks")
async def get_fast_vehicles(
    job_id: str,
    threshold: float = Query(15.0, ge=1.0, description="Speed threshold in px/frame"),
):
    """Filtre les trajectoires pour afficher uniquement les vehicules rapides.
    
    Les vehicules sont consideres comme rapides s'ils depassent le seuil de vitesse
    specifie (en pixels/frame).
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    tracks = job["result"]["tracks"]
    fast = [t for t in tracks if t["speed_pixels_per_frame"] > threshold]
    return {
        "job_id": job_id,
        "threshold_px_per_frame": threshold,
        "fast_vehicle_count": len(fast),
        "fast_tracks": fast,
    }


@router.get("/{job_id}/trajectory/{track_id}", summary="Get trajectory for a specific vehicle")
async def get_trajectory(job_id: str, track_id: int):
    """Recupere la trajectoire complete d'un vehicule specifique.
    
    Retourne :
    - Historique de positions (coordonnees x,y au fil du temps)
    - Vitesse moyenne et maximale du vehicule
    - Metadonnees et direction de deplacement
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    tracks = {t["track_id"]: t for t in job["result"]["tracks"]}
    if track_id not in tracks:
        raise HTTPException(404, f"Track ID {track_id} not found")

    return tracks[track_id]
