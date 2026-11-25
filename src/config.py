from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "T1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
METRICS_DIR = OUTPUT_DIR / "metrics"
FIGURES_DIR = OUTPUT_DIR / "figures"
MODELS_DIR = OUTPUT_DIR / "models"

RANDOM_STATE = 42
DEFAULT_CV_FOLDS = 5
DEFAULT_MAD_K = 3.0
DEFAULT_UNDERPERFORMANCE_RATIO = 0.5
WIND_LOWER = 0.0
WIND_UPPER = 26.0

OUTLIER_RULE_LABELS = {
    "negative_power": "Negative active power",
    "over_rated_power": "Power above rated limit",
    "downtime": "Zero power above cut-in (downtime)",
    "underperformance": "Underperformance vs theoretical curve",
    "bin_mad_outlier": "Statistical outlier within wind bin (MAD)",
}

DEFAULT_OUTLIER_RULES = {key: True for key in OUTLIER_RULE_LABELS}
