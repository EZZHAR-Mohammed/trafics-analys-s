# core/config.py
# Paramètres globaux du backend FastAPI et de l'analyse vidéo.
# Les valeurs peuvent être surchargées via un fichier .env.
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Métadonnées de l'application
    APP_NAME: str = "Traffic Analysis API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Dossiers de stockage
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    FRAMES_DIR: str = "outputs/frames"

    # Paramètres par défaut Lucas-Kanade (optique clairsemé)
    LK_MAX_CORNERS: int = 300
    LK_QUALITY_LEVEL: float = 0.3
    LK_MIN_DISTANCE: float = 7.0
    LK_BLOCK_SIZE: int = 7
    LK_WIN_SIZE: tuple = (15, 15)
    LK_MAX_LEVEL: int = 2

    # Paramètres par défaut Farneback (optique dense)
    FB_PYR_SCALE: float = 0.5
    FB_LEVELS: int = 3
    FB_WINSIZE: int = 15
    FB_ITERATIONS: int = 3
    FB_POLY_N: int = 5
    FB_POLY_SIGMA: float = 1.2
    FB_FLAGS: int = 0

    # Paramètres de suivi de piste
    TRACK_HISTORY_LEN: int = 30
    SPEED_ALERT_THRESHOLD: float = 15.0   # seuil de vitesse en pixels/frame

    # Paramètres d'alerte
    MOTION_THRESHOLD: float = 2.0         # seuil de magnitude moyenne du flux
    ALERT_COOLDOWN_FRAMES: int = 30       # délai entre deux alertes identiques

    # Paramètres d'export vidéo
    OUTPUT_FPS: int = 20
    OUTPUT_CODEC: str = "mp4v"

    class Config:
        env_file = ".env"


settings = Settings()
