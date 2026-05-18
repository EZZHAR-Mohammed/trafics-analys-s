# routers/alerts.py
"""
Endpoints pour recuperer les alertes generees durant un job de traitement.

Ce module permet de consulter les alertes detectees par le moteur d'analyse :
- Alertes de mouvement anormal
- Alertes de vehicules rapides
- Alertes de congestion et d'arret soudain
"""

from fastapi import APIRouter, HTTPException, Query
from services.video_processor import get_job

router = APIRouter()


@router.get("/{job_id}/all", summary="Get all alerts for a job")
async def get_alerts(job_id: str):
    """Retourne toutes les alertes declenchees durant le traitement video.
    
    Inclut le nombre total d'alertes et la liste detaillee
    avec timestamps, types et descriptions.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")
    return {
        "job_id": job_id,
        "total_alerts": len(job["result"]["alerts"]),
        "alerts": job["result"]["alerts"],
    }


@router.get("/{job_id}/by-type", summary="Filter alerts by type")
async def get_alerts_by_type(
    job_id: str,
    alert_type: str = Query(..., description="e.g. high_motion, fast_vehicle, motion_spike, congestion, sudden_stop"),
):
    """Filtre les alertes par type (mouvement eleve, vehicule rapide, etc.).
    
    Permet une analyse ciblee des types d'anomalies detectees.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    filtered = [a for a in job["result"]["alerts"] if a["alert_type"] == alert_type]
    return {
        "job_id": job_id,
        "alert_type": alert_type,
        "count": len(filtered),
        "alerts": filtered,
    }


@router.get("/{job_id}/timeline", summary="Alert timeline (grouped by second)")
async def alert_timeline(job_id: str):
    """Groupe les alertes par seconde pour une visualisation temporelle.
    
    Permet de voir quand les alertes se sont produites dans la video.
    Utile pour identifier les pics d'activite anormale.
    """
    job = get_job(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Job not found or not complete")

    from collections import defaultdict
    timeline = defaultdict(list)
    for a in job["result"]["alerts"]:
        sec = int(a["timestamp_sec"])
        timeline[sec].append(a["alert_type"])

    return {
        "job_id": job_id,
        "timeline": [{"second": k, "alerts": v} for k, v in sorted(timeline.items())],
    }
