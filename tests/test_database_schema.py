"""
Test database schema creation and validation.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


class TestDatabaseSchema:
    """Test suite for PostgreSQL database schema."""

    @pytest.fixture(scope="class")
    def db_engine(self):
        """Create test database engine."""
        # Use test database
        DATABASE_URL = "postgresql://hazeuser:testpassword@localhost:5432/haze_prediction_test"
        engine = create_engine(DATABASE_URL)
        yield engine
        engine.dispose()

    @pytest.fixture(scope="class")
    def db_session(self, db_engine):
        """Create database session."""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.close()

    def test_fire_detections_table_exists(self, db_engine):
        """Test that fire_detections table exists."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'fire_detections' in tables, "fire_detections table should exist"

    def test_fire_detections_columns(self, db_engine):
        """Test that fire_detections has correct columns."""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('fire_detections')}

        expected_columns = [
            'id', 'timestamp', 'latitude', 'longitude', 'frp',
            'brightness', 'confidence', 'acq_date', 'acq_time',
            'satellite', 'created_at'
        ]

        for col_name in expected_columns:
            assert col_name in columns, f"Column {col_name} should exist in fire_detections"

    def test_weather_data_table_exists(self, db_engine):
        """Test that weather_data table exists."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'weather_data' in tables, "weather_data table should exist"

    def test_weather_data_columns(self, db_engine):
        """Test that weather_data has correct columns."""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('weather_data')}

        expected_columns = [
            'id', 'location', 'latitude', 'longitude', 'timestamp',
            'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m',
            'wind_direction_10m', 'wind_gusts_10m', 'pressure_msl',
            'is_forecast', 'created_at'
        ]

        for col_name in expected_columns:
            assert col_name in columns, f"Column {col_name} should exist in weather_data"

    def test_psi_readings_table_exists(self, db_engine):
        """Test that psi_readings table exists."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'psi_readings' in tables, "psi_readings table should exist"

    def test_psi_readings_columns(self, db_engine):
        """Test that psi_readings has correct columns."""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('psi_readings')}

        expected_columns = [
            'id', 'timestamp', 'region', 'psi_24h', 'pm25_24h',
            'pm10_24h', 'o3_sub_index', 'co_sub_index',
            'no2_1h_max', 'so2_24h', 'created_at'
        ]

        for col_name in expected_columns:
            assert col_name in columns, f"Column {col_name} should exist in psi_readings"

    def test_predictions_table_exists(self, db_engine):
        """Test that predictions table exists."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'predictions' in tables, "predictions table should exist"

    def test_predictions_columns(self, db_engine):
        """Test that predictions has correct columns."""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('predictions')}

        expected_columns = [
            'id', 'prediction_timestamp', 'target_timestamp', 'horizon',
            'predicted_psi', 'confidence_lower', 'confidence_upper',
            'fire_risk_score', 'wind_transport_score', 'baseline_score',
            'model_version', 'created_at'
        ]

        for col_name in expected_columns:
            assert col_name in columns, f"Column {col_name} should exist in predictions"

    def test_validation_results_table_exists(self, db_engine):
        """Test that validation_results table exists."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'validation_results' in tables, "validation_results table should exist"

    def test_validation_results_columns(self, db_engine):
        """Test that validation_results has correct columns."""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('validation_results')}

        expected_columns = [
            'id', 'prediction_id', 'actual_psi', 'absolute_error',
            'squared_error', 'validated_at'
        ]

        for col_name in expected_columns:
            assert col_name in columns, f"Column {col_name} should exist in validation_results"

    def test_fire_detections_indexes(self, db_engine):
        """Test that fire_detections has required indexes."""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes('fire_detections')
        index_names = [idx['name'] for idx in indexes]

        assert 'idx_fire_timestamp' in index_names, "Should have timestamp index"
        assert 'idx_fire_location' in index_names, "Should have location index"

    def test_psi_unique_constraint(self, db_engine):
        """Test that psi_readings has unique constraint on timestamp+region."""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes('psi_readings')

        # Check for unique index
        unique_indexes = [idx for idx in indexes if idx.get('unique', False)]
        assert len(unique_indexes) > 0, "Should have at least one unique index"
