# core/logger.py
# Configuration basique des logs pour l'application.
# Les messages sont envoyés sur la sortie standard afin d'être visibles en console.
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("traffic_analysis")
