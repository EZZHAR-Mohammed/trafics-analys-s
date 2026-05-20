# services/optical_flow_engine.py
"""
Moteur de calcul du flux optique.
Ce module fournit :
- Lucas-Kanade (flot optique sparse / clairsemé)
- Farneback (flot optique dense)
- Visualisation sur image
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from core.config import settings
from core.logger import logger


@dataclass
class LKResult:
    good_new: np.ndarray          # tracked points in new frame
    good_old: np.ndarray          # tracked points in old frame
    vectors: np.ndarray           # displacement vectors
    magnitudes: np.ndarray
    angles: np.ndarray
    avg_magnitude: float
    max_magnitude: float
    point_count: int
    processing_ms: float
    frame_with_flow: np.ndarray   # visualized frame


@dataclass
class FBResult:
    flow: np.ndarray              # raw HxWx2 flow field
    magnitude: np.ndarray
    angle: np.ndarray
    avg_magnitude: float
    max_magnitude: float
    hsv_visualization: np.ndarray
    arrow_visualization: np.ndarray
    processing_ms: float


class LucasKanadeEngine:
    """Calcul du flux optique sparse avec Lucas-Kanade pyramidal.
    
    Cette methode :
    - Detecte automatiquement les coins pertinents (features) de la frame
    - Suit ces points de frame a frame avec la methode Lucas-Kanade pyramidale
    - Retourne les positions anciennes/nouvelles et les vecteurs de deplacement
    - Ideal pour le suivi d'objets et le comptage de vehicules (sparse = efficace)
    """

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.feature_params = dict(
            maxCorners=p.get("max_corners", settings.LK_MAX_CORNERS),
            qualityLevel=p.get("quality_level", settings.LK_QUALITY_LEVEL),
            minDistance=p.get("min_distance", settings.LK_MIN_DISTANCE),
            blockSize=p.get("block_size", settings.LK_BLOCK_SIZE),
        )
        win = p.get("win_size", settings.LK_WIN_SIZE[0])
        self.lk_params = dict(
            winSize=(win, win),
            maxLevel=p.get("max_level", settings.LK_MAX_LEVEL),
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
        )
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_points: Optional[np.ndarray] = None
        self.colors = np.random.randint(0, 255, (2000, 3))

    def reset(self):
        self.prev_gray = None
        self.prev_points = None

    def process_frame(self, frame: np.ndarray, roi: Optional[Dict] = None) -> Optional[LKResult]:
        """Traite une frame avec Lucas-Kanade.

        Si c'est la premiere frame, detecte les coins et retourne None.
        Pour les frames suivantes, suit les coins et retourne les resultats.

        Args:
            frame : image BGR de la video
            roi : zone d'interet optionnelle pour limiter le calcul

        Returns:
            LKResult ou None si le suivi ne peut pas encore etre calcule.
        """
        t0 = time.perf_counter()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Applique un masque ROI si specifie
        if roi:
            mask_gray = np.zeros_like(gray)
            x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
            mask_gray[y:y+h, x:x+w] = gray[y:y+h, x:x+w]
            gray = mask_gray

        if self.prev_gray is None or self.prev_points is None or len(self.prev_points) == 0:
            self.prev_gray = gray.copy()
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return None

        if self.prev_points is None or len(self.prev_points) == 0:
            self.prev_gray = gray.copy()
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return None

        # Calcul du flux optique Lucas-Kanade pyramidal
        # Retourne les points suivis, leur etat (1=bon, 0=perdu) et erreur de suivi
        new_points, status, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, self.prev_points, None, **self.lk_params
        )

        if new_points is None:
            self.prev_gray = gray.copy()
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return None

        # Filtre les points avec statut 1 (points bien suivis)
        good_new = new_points[status == 1]
        good_old = self.prev_points[status == 1]

        # Calcul des vecteurs de deplacement et des statistiques de flux
        vectors = good_new - good_old
        magnitudes = np.linalg.norm(vectors, axis=1)
        angles = np.degrees(np.arctan2(vectors[:, 1], vectors[:, 0]))

        # Visualisation du flux sur la frame
        vis = frame.copy()
        mask = np.zeros_like(frame)
        for i, (new, old) in enumerate(zip(good_new, good_old)):
            a, b = new.ravel().astype(int)
            c, d = old.ravel().astype(int)
            color = self.colors[i % len(self.colors)].tolist()
            cv2.line(mask, (a, b), (c, d), color, 2)
            cv2.circle(vis, (a, b), 5, color, -1)
        vis = cv2.add(vis, mask)

        # Update
        self.prev_gray = gray.copy()
        # Refresh corners every frame or keep tracking
        if len(good_new) < 50:
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
        else:
            self.prev_points = good_new.reshape(-1, 1, 2)

        elapsed = (time.perf_counter() - t0) * 1000
        return LKResult(
            good_new=good_new,
            good_old=good_old,
            vectors=vectors,
            magnitudes=magnitudes,
            angles=angles,
            avg_magnitude=float(np.mean(magnitudes)) if len(magnitudes) > 0 else 0.0,
            max_magnitude=float(np.max(magnitudes)) if len(magnitudes) > 0 else 0.0,
            point_count=len(good_new),
            processing_ms=elapsed,
            frame_with_flow=vis,
        )


class FarnebackEngine:
    """Calcul du flux optique dense avec l'algorithme Farneback.
    
    Cette methode :
    - Calcule le flux optique sur tous les pixels (dense) de l'image
    - Approxime l'algorithme Horn-Schunck avec polynomes locaux
    - Produit un champ de flux complet (HxWx2) avec vecteurs pour chaque pixel
    - Ideal pour analyser les zones entieres et deriver le mouvement global
    """

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.pyr_scale = p.get("pyr_scale", settings.FB_PYR_SCALE)
        self.levels = p.get("levels", settings.FB_LEVELS)
        self.winsize = p.get("winsize", settings.FB_WINSIZE)
        self.iterations = p.get("iterations", settings.FB_ITERATIONS)
        self.poly_n = p.get("poly_n", settings.FB_POLY_N)
        self.poly_sigma = p.get("poly_sigma", settings.FB_POLY_SIGMA)
        self.flags = p.get("flags", settings.FB_FLAGS)
        self.prev_gray: Optional[np.ndarray] = None

    def reset(self):
        self.prev_gray = None

    def process_frame(self, frame: np.ndarray, roi: Optional[Dict] = None) -> Optional[FBResult]:
        """Traite une frame avec Farneback (flux optique dense).

        La premiere frame est conservee en reference pour le calcul.
        Pour les frames suivantes, calcule le flux dense et retourne les resultats.

        Args:
            frame : image BGR de la video
            roi : zone d'interet optionnelle pour limiter le calcul

        Returns:
            FBResult ou None si la frame de reference n'est pas encore disponible.
        """
        t0 = time.perf_counter()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if roi:
            mask_gray = np.zeros_like(gray)
            x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
            mask_gray[y:y+h, x:x+w] = gray[y:y+h, x:x+w]
            gray = mask_gray

        if self.prev_gray is None:
            self.prev_gray = gray.copy()
            return None

        # Calcul du flux optique Farneback dense
        # Retourne un champ de flux (HxWx2) avec la composante vx, vy par pixel
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray,
            None,
            self.pyr_scale, self.levels, self.winsize,
            self.iterations, self.poly_n, self.poly_sigma, self.flags,
        )

        # Conversion des composantes cartesiennes en magnitude et angle
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # Visualisation HSV du flux (teinte = direction, saturation = 255, valeur = magnitude)
        hsv = np.zeros((*gray.shape, 3), dtype=np.uint8)
        hsv[..., 1] = 255
        hsv[..., 0] = (angle * 180 / np.pi / 2).astype(np.uint8)
        hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        hsv_vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # Visualisation avec fleches (sous-echantillonnage pour lisibilite)
        arrow_vis = frame.copy()
        step = 16  # Grille de sous-echantillonnage pour eviter la surcharge visuelle
        h, w = gray.shape
        for y in range(0, h, step):
            for x in range(0, w, step):
                fx, fy = flow[y, x]
                mag = np.sqrt(fx**2 + fy**2)
                if mag > 0.5:  # Affiche seulement les fleches avec mouvement visible
                    end = (int(x + fx * 3), int(y + fy * 3))
                    cv2.arrowedLine(arrow_vis, (x, y), end, (0, 255, 0), 1, tipLength=0.3)

        self.prev_gray = gray.copy()
        elapsed = (time.perf_counter() - t0) * 1000

        return FBResult(
            flow=flow,
            magnitude=magnitude,
            angle=angle,
            avg_magnitude=float(np.mean(magnitude)),
            max_magnitude=float(np.max(magnitude)),
            hsv_visualization=hsv_vis,
            arrow_visualization=arrow_vis,
            processing_ms=elapsed,
        )


class OpticalFlowEngine:
    """Moteur unifie de flux optique combinant Lucas-Kanade et Farneback.
    
    Cette classe :
    - Encapsule les deux moteurs de flux optique (LK et Farneback)
    - Permet de traiter une frame avec une ou les deux methodes
    - Fournit une interface unique pour la pipeline video
    """

    def __init__(self, lk_params=None, fb_params=None):
        self.lk = LucasKanadeEngine(lk_params)
        self.fb = FarnebackEngine(fb_params)

    def reset(self):
        self.lk.reset()
        self.fb.reset()

    def process(self, frame: np.ndarray, method: str = "both", roi=None):
        results = {}
        if method in ("lucas_kanade", "both"):
            results["lk"] = self.lk.process_frame(frame, roi)
        if method in ("farneback", "both"):
            results["fb"] = self.fb.process_frame(frame, roi)
        return results
