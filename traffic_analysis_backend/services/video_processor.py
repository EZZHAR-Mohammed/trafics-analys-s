# services/video_processor.py
"""
Pipeline de traitement vidéo pour le backend.
- Lit chaque frame de la vidéo
- Applique le flux optique (Lucas-Kanade et/ou Farneback)
- Suit les objets détectés
- Déclenche les alertes
- Sauvegarde la vidéo annotée et les frames exportables
"""

import cv2
import numpy as np
import uuid
import time
import os
from typing import Optional, Dict, Any, List

from core.config import settings
from core.logger import logger
from services.optical_flow_engine import OpticalFlowEngine
from services.tracker import VehicleTracker
from services.alert_engine import AlertEngine


# Stockage en mémoire des jobs traités.
# Ce mode est temporaire : un redémarrage du serveur efface l'historique.
# Chaque job conserve son statut, son pourcentage d'avancement et le résultat final.
_jobs: Dict[str, Dict[str, Any]] = {}


def get_job(job_id: str) -> Optional[Dict]:
    """Retourne le job en cours ou termine correspondant a job_id."""
    return _jobs.get(job_id)


def list_jobs() -> List[Dict]:
    """Liste les jobs existants avec leur statut et date de création."""
    return [{"job_id": jid, "status": j["status"], "created_at": j["created_at"]}
            for jid, j in _jobs.items()]


def process_video(
    video_path: str,
    method: str = "both",
    lk_params: Optional[Dict] = None,
    fb_params: Optional[Dict] = None,
    roi: Optional[Dict] = None,
    enable_tracking: bool = True,
    enable_alerts: bool = True,
    speed_alert_threshold: float = 15.0,
    motion_threshold: float = 2.0,
    save_output: bool = True,
    max_frames: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute le pipeline video principal pour un fichier.

    Etapes :
    1. Creation d'un identifiant de job et stockage en memoire
    2. Ouverture de la video et lecture des proprietes (FPS, dimension, nb frames)
    3. Initialisation des moteurs de flux optique, du tracker et du moteur d'alertes
    4. Lecture frame par frame du fichier video
    5. Calcul des flux optiques Lucas-Kanade et/ou Farneback
    6. Mise a jour du suivi des trajectoires
    7. Detection des alertes en fonction des mouvements et vitesses
    8. Annotation et sauvegarde des frames, ecriture de la video de sortie
    9. Resume des resultats et mise a jour du statut du job
    """
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "processing", "created_at": time.time(), "progress": 0}
    frames_dir = os.path.join(settings.FRAMES_DIR, job_id)
    os.makedirs(frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        _jobs[job_id]["status"] = "error"
        raise ValueError(f"Cannot open video: {video_path}")

    fps_orig = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if max_frames:
        total_frames = min(total_frames, max_frames)

    # Prépare l'écriture de la vidéo annotée si demandé.
    out_writer = None
    out_path = None
    if save_output:
        out_path = os.path.join(settings.OUTPUT_DIR, f"result_{job_id}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*settings.OUTPUT_CODEC)
        out_w = width * 2 if method == "both" else width
        out_writer = cv2.VideoWriter(out_path, fourcc, settings.OUTPUT_FPS, (out_w, height))
        # La video resultat est ecrite avec deux vues cote a cote si les deux methodes sont actives.

    # Initialisation des moteurs de calcul.
    flow_engine = OpticalFlowEngine(lk_params, fb_params)
    tracker = VehicleTracker()
    alert_eng = AlertEngine(motion_threshold=motion_threshold, speed_threshold=speed_alert_threshold)

    frame_results = []
    lk_fps_list = []
    fb_fps_list = []
    frame_idx = 0
    t_pipeline_start = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret or (max_frames and frame_idx >= max_frames):
            break

        t0 = time.perf_counter()
        timestamp = frame_idx / fps_orig

        # Calcul du flux optique selon la methode demandee
        results = flow_engine.process(frame, method=method, roi=roi)
        lk_res = results.get("lk")
        fb_res = results.get("fb")

        # Mise a jour du tracker sur les points Lucas-Kanade.
        if enable_tracking and lk_res:
            tracker.update(lk_res.good_new, lk_res.good_old)

        track_stats = tracker.get_stats()

        # Vérification des alertes si activées.
        alert_triggered = False
        avg_mag = (lk_res.avg_magnitude if lk_res else 0) or (fb_res.avg_magnitude if fb_res else 0)
        max_mag = (lk_res.max_magnitude if lk_res else 0)

        if enable_alerts:
            triggered = alert_eng.check_flow(
                frame_idx=frame_idx,
                timestamp=timestamp,
                avg_magnitude=avg_mag,
                max_magnitude=max_mag,
                active_tracks=track_stats["active_tracks"],
                max_track_speed=track_stats["max_speed"],
            )
            alert_triggered = len(triggered) > 0
            # Les alertes sont stockees dans alert_eng et ajoutees au resume final.
        proc_ms = (time.perf_counter() - t0) * 1000

        frame_results.append({
            "frame_index": frame_idx,
            "timestamp_sec": round(timestamp, 3),
            "lk_point_count": lk_res.point_count if lk_res else None,
            "lk_avg_magnitude": round(lk_res.avg_magnitude, 3) if lk_res else None,
            "fb_avg_magnitude": round(fb_res.avg_magnitude, 3) if fb_res else None,
            "fb_max_magnitude": round(fb_res.max_magnitude, 3) if fb_res else None,
            "motion_detected": avg_mag > motion_threshold,
            "alert_triggered": alert_triggered,
            "active_tracks": track_stats["active_tracks"],
            "processing_time_ms": round(proc_ms, 2),
        })

        if lk_res:
            lk_fps_list.append(1000.0 / max(lk_res.processing_ms, 0.001))
        if fb_res:
            fb_fps_list.append(1000.0 / max(fb_res.processing_ms, 0.001))

        lk_frame = (tracker.draw_tracks(lk_res.frame_with_flow)
                    if lk_res and enable_tracking else (lk_res.frame_with_flow if lk_res else frame))
        fb_frame = fb_res.arrow_visualization if fb_res else frame
        # Choix de la frame de sortie selon la methode demandee (LK, FB ou les deux).
        # Indicateur visuel d'alerte.
        if alert_triggered:
            for f in [lk_frame, fb_frame]:
                cv2.rectangle(f, (0, 0), (f.shape[1], 40), (0, 0, 200), -1)
                cv2.putText(f, "ALERT", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        # Ajoute un label sur la frame selon la méthode.
        if lk_frame is not None:
            cv2.putText(lk_frame, "Lucas-Kanade (Sparse)", (10, height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
        if fb_frame is not None:
            cv2.putText(fb_frame, "Farneback (Dense)", (10, height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        if method == "both" and lk_frame is not None and fb_frame is not None:
            combined = np.hstack([lk_frame, fb_frame])
        elif method == "lucas_kanade" and lk_frame is not None:
            combined = lk_frame
        elif method == "farneback" and fb_frame is not None:
            combined = fb_frame
        else:
            combined = frame

        # Sauvegarde la frame annotée pour l'export.
        frame_file = os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg")
        cv2.imwrite(frame_file, combined)

        if out_writer:
            out_writer.write(combined)

        frame_idx += 1
        _jobs[job_id]["progress"] = int(frame_idx / max(total_frames, 1) * 100)

    cap.release()
    if out_writer:
        out_writer.release()

    total_elapsed = time.perf_counter() - t_pipeline_start
    avg_fps = frame_idx / max(total_elapsed, 0.001)

    all_tracks = [t.to_dict() for t in tracker.tracks.values()]

    result = {
        "job_id": job_id,
        "video_path": video_path,
        "total_frames": total_frames,
        "processed_frames": frame_idx,
        "fps_original": round(fps_orig, 2),
        "avg_processing_fps": round(avg_fps, 2),
        "method": method,
        "frame_results": frame_results,
        "tracks": all_tracks,
        "alerts": [a.to_dict() for a in alert_eng.alerts],
        "output_video_url": f"/outputs/result_{job_id}.mp4" if out_path else None,
        "frames_dir": frames_dir,
        "frames_export_url": f"/api/v1/export/{job_id}/frames-zip",
        "stats": {
            "lk_avg_fps": round(float(np.mean(lk_fps_list)), 2) if lk_fps_list else None,
            "fb_avg_fps": round(float(np.mean(fb_fps_list)), 2) if fb_fps_list else None,
            "total_alerts": len(alert_eng.alerts),
            "alert_summary": alert_eng.get_summary(),
            "tracking": tracker.get_stats(),
        },
    }

    _jobs[job_id] = {"status": "done", "created_at": _jobs[job_id]["created_at"],
                     "progress": 100, "result": result}
    logger.info(f"✅ Job {job_id} done: {frame_idx} frames, {len(alert_eng.alerts)} alerts")
    return result
