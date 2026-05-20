# services/alert_engine.py
"""
Moteur d'alertes et de détection d'anomalies.
Détecte les événements de trafic anormaux à partir des magnitudes de flux et des vitesses de piste.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import deque
from core.config import settings
from core.logger import logger


@dataclass
class Alert:
    """Representation d'une alerte detectee sur une frame.

    Une alerte contient :
    - l'index de frame et le timestamp en secondes
    - le type d'alerte (high_motion, fast_vehicle, motion_spike, etc.)
    - la magnitude associee et une description lisible
    - une region optionnelle pour identifier la zone de l'alerte
    """
    frame_index: int
    timestamp_sec: float
    alert_type: str
    magnitude: float
    description: str
    region: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "timestamp_sec": round(self.timestamp_sec, 3),
            "alert_type": self.alert_type,
            "magnitude": round(self.magnitude, 2),
            "description": self.description,
            "region": self.region,
        }


class AlertEngine:
    """Moteur d'alertes base sur le flux optique et les vitesses de piste.

    Ce moteur detecte plusieurs categories d'anomalies :
    - mouvement fort (high_motion)
    - vehicule rapide (fast_vehicle)
    - pic de mouvement soudain (motion_spike)
    - arret brutal (sudden_stop)
    - congestion (nombre de pistes elevees avec peu de mouvement)
    """

    def __init__(
        self,
        motion_threshold: float = settings.MOTION_THRESHOLD,
        speed_threshold: float = settings.SPEED_ALERT_THRESHOLD,
        cooldown_frames: int = settings.ALERT_COOLDOWN_FRAMES,
    ):
        self.motion_threshold = motion_threshold
        self.speed_threshold = speed_threshold
        self.cooldown_frames = cooldown_frames

        self.alerts: List[Alert] = []
        self._last_alert_frame: Dict[str, int] = {}
        self._magnitude_history: deque = deque(maxlen=30)
        self._speed_history: deque = deque(maxlen=30)

    def reset(self):
        self.alerts.clear()
        self._last_alert_frame.clear()
        self._magnitude_history.clear()
        self._speed_history.clear()

    def _can_trigger(self, alert_type: str, frame_idx: int) -> bool:
        """Indique si une nouvelle alerte de type donne peut etre declenchee."""
        last = self._last_alert_frame.get(alert_type, -self.cooldown_frames)
        return (frame_idx - last) >= self.cooldown_frames

    def _register(self, alert: Alert):
        """Enregistre l'alerte et memorise sa derniere frame pour le cooldown."""
        self.alerts.append(alert)
        self._last_alert_frame[alert.alert_type] = alert.frame_index
        logger.info(f"🔥 ALERT [{alert.alert_type}] frame={alert.frame_index}: {alert.description}")

    def check_flow(
        self,
        frame_idx: int,
        timestamp: float,
        avg_magnitude: float,
        max_magnitude: float,
        active_tracks: int = 0,
        max_track_speed: float = 0.0,
    ) -> List[Alert]:
        """Analyse les statistiques de la frame et declenche les alertes correspondantes.

        Args:
            frame_idx : index de la frame actuelle
            timestamp : temps ecoule en secondes
            avg_magnitude : magnitude moyenne du flux optique
            max_magnitude : magnitude maximale du flux sur la frame
            active_tracks : nombre de pistes de suivi actives
            max_track_speed : vitesse maximale parmi les pistes

        Returns:
            Liste des alertes declenchees pour cette frame.
        """
        triggered = []
        self._magnitude_history.append(avg_magnitude)
        self._speed_history.append(max_track_speed)

        # 1. High motion alert
        if avg_magnitude > self.motion_threshold:
            if self._can_trigger("high_motion", frame_idx):
                a = Alert(
                    frame_index=frame_idx,
                    timestamp_sec=timestamp,
                    alert_type="high_motion",
                    magnitude=avg_magnitude,
                    description=f"High motion detected: avg={avg_magnitude:.2f} px/frame",
                )
                self._register(a)
                triggered.append(a)

        # 2. Fast vehicle alert
        if max_track_speed > self.speed_threshold:
            if self._can_trigger("fast_vehicle", frame_idx):
                a = Alert(
                    frame_index=frame_idx,
                    timestamp_sec=timestamp,
                    alert_type="fast_vehicle",
                    magnitude=max_track_speed,
                    description=f"Fast vehicle: {max_track_speed:.1f} px/frame (threshold={self.speed_threshold})",
                )
                self._register(a)
                triggered.append(a)

        # 3. Sudden motion spike
        if len(self._magnitude_history) >= 5:
            recent_avg = float(np.mean(list(self._magnitude_history)[-5:]))
            older_avg = float(np.mean(list(self._magnitude_history)[:-5])) if len(self._magnitude_history) > 5 else recent_avg
            if older_avg > 0.1 and (recent_avg / older_avg) > 3.0:
                if self._can_trigger("motion_spike", frame_idx):
                    a = Alert(
                        frame_index=frame_idx,
                        timestamp_sec=timestamp,
                        alert_type="motion_spike",
                        magnitude=recent_avg,
                        description=f"Sudden motion spike: {recent_avg:.2f} (x{recent_avg/older_avg:.1f} increase)",
                    )
                    self._register(a)
                    triggered.append(a)

        # 4. Sudden stop (motion drops to near zero after activity)
        if len(self._magnitude_history) >= 10:
            prev_avg = float(np.mean(list(self._magnitude_history)[-10:-3]))
            curr_avg = float(np.mean(list(self._magnitude_history)[-3:]))
            if prev_avg > 2.0 and curr_avg < 0.3:
                if self._can_trigger("sudden_stop", frame_idx):
                    a = Alert(
                        frame_index=frame_idx,
                        timestamp_sec=timestamp,
                        alert_type="sudden_stop",
                        magnitude=curr_avg,
                        description=f"Sudden stop detected: motion dropped from {prev_avg:.2f} to {curr_avg:.2f}",
                    )
                    self._register(a)
                    triggered.append(a)

        # 5. Congestion (many slow tracks)
        if active_tracks > 10 and avg_magnitude < 1.0:
            if self._can_trigger("congestion", frame_idx):
                a = Alert(
                    frame_index=frame_idx,
                    timestamp_sec=timestamp,
                    alert_type="congestion",
                    magnitude=avg_magnitude,
                    description=f"Congestion: {active_tracks} tracks with low motion {avg_magnitude:.2f}",
                )
                self._register(a)
                triggered.append(a)

        return triggered

    def get_summary(self) -> dict:
        """Retourne un resume agregant le nombre d'alertes par type."""
        if not self.alerts:
            return {"total_alerts": 0, "by_type": {}}
        from collections import Counter
        counts = Counter(a.alert_type for a in self.alerts)
        return {
            "total_alerts": len(self.alerts),
            "by_type": dict(counts),
        }
