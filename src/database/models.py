"""
Database models for Singapore Haze Prediction System.
SQLAlchemy ORM models matching the schema in TDD.md
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    DECIMAL, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class FireDetection(Base):
    """Fire detections from NASA FIRMS."""
    __tablename__ = 'fire_detections'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    latitude = Column(DECIMAL(10, 6), nullable=False)
    longitude = Column(DECIMAL(10, 6), nullable=False)
    frp = Column(DECIMAL(10, 2))  # Fire Radiative Power (MW)
    brightness = Column(DECIMAL(10, 2))
    confidence = Column(String(10))  # 'h', 'n', 'l'
    acq_date = Column(DateTime)
    acq_time = Column(String(10))
    satellite = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_fire_timestamp', 'timestamp'),
        Index('idx_fire_location', 'latitude', 'longitude'),
    )


class WeatherData(Base):
    """Weather data from Open-Meteo API."""
    __tablename__ = 'weather_data'

    id = Column(Integer, primary_key=True)
    location = Column(String(100))
    latitude = Column(DECIMAL(10, 6))
    longitude = Column(DECIMAL(10, 6))
    timestamp = Column(DateTime, nullable=False)
    temperature_2m = Column(DECIMAL(5, 2))
    relative_humidity_2m = Column(DECIMAL(5, 2))
    wind_speed_10m = Column(DECIMAL(5, 2))
    wind_direction_10m = Column(DECIMAL(5, 2))
    wind_gusts_10m = Column(DECIMAL(5, 2))
    pressure_msl = Column(DECIMAL(7, 2))
    is_forecast = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_weather_timestamp', 'timestamp'),
        Index('idx_weather_location', 'location', 'timestamp'),
    )


class PSIReading(Base):
    """PSI readings from Singapore NEA."""
    __tablename__ = 'psi_readings'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    region = Column(String(20))  # 'national', 'north', 'south', etc.
    psi_24h = Column(Integer)
    pm25_24h = Column(Integer)
    pm10_24h = Column(Integer)
    o3_sub_index = Column(Integer)
    co_sub_index = Column(Integer)
    no2_1h_max = Column(Integer)
    so2_24h = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_psi_timestamp', 'timestamp'),
        UniqueConstraint('timestamp', 'region', name='idx_psi_unique'),
    )


class Prediction(Base):
    """PSI predictions from our model."""
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True)
    prediction_timestamp = Column(DateTime, nullable=False)  # When prediction was made
    target_timestamp = Column(DateTime, nullable=False)      # When PSI is predicted for
    horizon = Column(String(10), nullable=False)             # '24h', '48h', '72h', '7d'
    predicted_psi = Column(DECIMAL(10, 2), nullable=False)
    confidence_lower = Column(DECIMAL(10, 2))
    confidence_upper = Column(DECIMAL(10, 2))
    fire_risk_score = Column(DECIMAL(5, 2))
    wind_transport_score = Column(DECIMAL(5, 2))
    baseline_score = Column(DECIMAL(5, 2))
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

    # Relationship to validation results
    validations = relationship("ValidationResult", back_populates="prediction")

    __table_args__ = (
        Index('idx_predictions_target', 'target_timestamp', 'horizon'),
        Index('idx_predictions_created', 'prediction_timestamp'),
    )


class ValidationResult(Base):
    """Validation results comparing predictions to actual PSI."""
    __tablename__ = 'validation_results'

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey('predictions.id'))
    actual_psi = Column(Integer)
    absolute_error = Column(DECIMAL(10, 2))
    squared_error = Column(DECIMAL(10, 2))
    validated_at = Column(DateTime, default=datetime.now)

    # Relationship to prediction
    prediction = relationship("Prediction", back_populates="validations")

    __table_args__ = (
        Index('idx_validation_prediction', 'prediction_id'),
    )
