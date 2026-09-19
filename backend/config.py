from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(_project_root() / "data" / "screening_history.sqlite3"))
    MODEL_DIR: str = os.getenv("MODEL_DIR", str(_project_root() / "models"))
    REPORT_DIR: str = os.getenv("REPORT_DIR", str(_project_root() / "reports"))
    RAW_DATA_DIR: str = os.getenv("RAW_DATA_DIR", str(_project_root() / "data" / "raw"))
    T21_LOW_THRESHOLD: float = float(os.getenv("T21_LOW_THRESHOLD", "0.15"))
    T21_HIGH_THRESHOLD: float = float(os.getenv("T21_HIGH_THRESHOLD", "0.35"))
    T18_LOW_THRESHOLD: float = float(os.getenv("T18_LOW_THRESHOLD", "0.10"))
    T18_HIGH_THRESHOLD: float = float(os.getenv("T18_HIGH_THRESHOLD", "0.30"))
    TITLE: str = "Prenatal AI Screening"
    DISCLAIMER: str = (
        "This application is an academic research prototype for prenatal screening risk estimation. "
        "It is not a medical diagnostic tool and must not be used independently for clinical decision-making. "
        "Results should be interpreted only by qualified healthcare professionals and, where appropriate, confirmed using established clinical diagnostic procedures."
    )


def get_config() -> Config:
    return Config()
