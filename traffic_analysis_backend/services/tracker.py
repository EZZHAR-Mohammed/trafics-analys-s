# services/tracker.py
"""
Tracker de véhicules basé sur des points de flux optique.
Il relie les points détectés frame après frame pour construire des trajectoires.
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from core.config import settings
from core.logger import logger


@dataclass
class Track:
    """Representation d'une piste de vehicule construite a partir de points de flux optique.

    Une piste conserve :
    - l'identifiant de la piste
    - l'historique des positions recents
    - l'historique des vitesses pour calculer la vitesse moyenne
    - une couleur d'affichage pour la visualisation
    """
    track_id: int
    positions: deque = field(default_factory=lambda: deque(maxlen=settings.TRACK_HISTORY_LEN))
    speeds: deque = field(default_factory=lambda: deque(maxlen=30))
    color: Tuple[int, int, int] = (0, 255, 0)

    @property
    def current_pos(self) -> Optional[np.ndarray]:
        return self.positions[-1] if self.positions else None

    @property
    def avg_speed(self) -> float:
        return float(np.mean(self.speeds)) if self.speeds else 0.0

    @property
    def direction_angle(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        dx = self.positions[-1][0] - self.positions[-2][0]
        dy = self.positions[-1][1] - self.positions[-2][1]
        return float(np.degrees(np.arctan2(dy, dx)))

    @property
    def is_fast(self) -> bool:
        return self.avg_speed > settings.SPEED_ALERT_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "track_id": int(self.track_id),
            "positions": [[float(x), float(y)] for x, y in self.positions],
            "speed_pixels_per_frame": round(float(self.avg_speed), 2),
            "direction_angle_deg": round(float(self.direction_angle), 2),
            "is_fast": bool(self.is_fast),
            "color": [int(c) for c in self.color],
        }


class VehicleTracker:
    """Suivi multi-objets simplifie a partir des points Lucas-Kanade.

    Le tracker associe les nouveaux points de flux optique aux trajets existants
    par plus proche voisin, supprime les pistes disparues et cree de nouvelles
    pistes pour les points non apparies.
    """

    def __init__(self, max_missing: int = 10, merge_distance: float = 30.0):
        self.tracks: Dict[int, Track] = {}
        self._next_id = 0
        self.max_missing = max_missing
        self.merge_distance = merge_distance
        self._missing_count: Dict[int, int] = {}
        self._colors = np.random.randint(80, 255, (1000, 3)).tolist()

    def reset(self):
        self.tracks.clear()
        self._missing_count.clear()
        self._next_id = 0

    def update(self, good_new: np.ndarray, good_old: np.ndarray) -> Dict[int, Track]:
        """Met a jour les tracks avec les nouveaux points de flux Lucas-Kanade.

        Args:
            good_new : points courants suivis dans la frame actuelle
            good_old : points precedents correspondants dans la frame precedente

        Returns:
            Dictionnaire des tracks actives mis a jour.
        """
        if len(good_new) == 0:
            # Increment missing counters
            for tid in list(self.tracks.keys()):
                self._missing_count[tid] = self._missing_count.get(tid, 0) + 1
                if self._missing_count[tid] > self.max_missing:
                    del self.tracks[tid]
                    del self._missing_count[tid]
            return self.tracks

        unmatched_points = list(range(len(good_new)))

        # Try to match each existing track
        for tid, track in list(self.tracks.items()):
            if track.current_pos is None:
                continue
            best_dist = self.merge_distance
            best_idx = -1
            for i in unmatched_points:
                d = np.linalg.norm(good_old[i] - track.current_pos)
                if d < best_dist:
                    best_dist = d
                    best_idx = i

            if best_idx >= 0:
                new_pos = good_new[best_idx]
                speed = np.linalg.norm(new_pos - good_old[best_idx])
                track.positions.append(new_pos)
                track.speeds.append(speed)
                self._missing_count[tid] = 0
                unmatched_points.remove(best_idx)
            else:
                self._missing_count[tid] = self._missing_count.get(tid, 0) + 1
                if self._missing_count[tid] > self.max_missing:
                    del self.tracks[tid]
                    self._missing_count.pop(tid, None)

        # Create new tracks for unmatched points
        for i in unmatched_points:
            tid = self._next_id
            self._next_id += 1
            color = tuple(self._colors[tid % len(self._colors)])
            t = Track(track_id=tid, color=color)
            t.positions.append(good_new[i])
            speed = np.linalg.norm(good_new[i] - good_old[i])
            t.speeds.append(speed)
            self.tracks[tid] = t
            self._missing_count[tid] = 0

        return self.tracks

    def draw_tracks(self, frame: np.ndarray) -> np.ndarray:
        """Dessine les trajectoires, directions et vitesses des tracks sur une image."""
        out = frame.copy()
        for tid, track in self.tracks.items():
            positions = list(track.positions)
            color = track.color
            # Draw trajectory
            for i in range(1, len(positions)):
                pt1 = tuple(positions[i - 1].astype(int))
                pt2 = tuple(positions[i].astype(int))
                cv2.line(out, pt1, pt2, color, 2)

            # Draw current position dot
            if len(positions) >= 1:
                pt = tuple(positions[-1].astype(int))
                cv2.circle(out, pt, 6, color, -1)

                # Speed label
                speed_txt = f"#{tid} {track.avg_speed:.1f}px/f"
                label_color = (0, 0, 255) if track.is_fast else (255, 255, 255)
                cv2.putText(out, speed_txt, (pt[0] + 8, pt[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, label_color, 1, cv2.LINE_AA)

                # Direction arrow
                if len(positions) >= 2:
                    dx = positions[-1][0] - positions[-2][0]
                    dy = positions[-1][1] - positions[-2][1]
                    norm = max(np.sqrt(dx**2 + dy**2), 1e-5)
                    scale = 20
                    ep = (int(pt[0] + dx / norm * scale), int(pt[1] + dy / norm * scale))
                    cv2.arrowedLine(out, pt, ep, (0, 255, 255), 2, tipLength=0.4)

        return out

    def get_stats(self) -> dict:
        """Retourne des statistiques agregees sur les tracks actives."""
        if not self.tracks:
            return {"active_tracks": 0, "fast_vehicles": 0, "avg_speed": 0.0, "max_speed": 0.0}
        speeds = [t.avg_speed for t in self.tracks.values()]
        return {
            "active_tracks": len(self.tracks),
            "fast_vehicles": sum(1 for t in self.tracks.values() if t.is_fast),
            "avg_speed": round(float(np.mean(speeds)), 2),
            "max_speed": round(float(np.max(speeds)), 2),
        }