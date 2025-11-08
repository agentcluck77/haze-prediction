"""Data ingestion modules for Singapore Haze Prediction System."""

from .firms import fetch_recent_fires, save_fires_to_db

__all__ = ['fetch_recent_fires', 'save_fires_to_db']
