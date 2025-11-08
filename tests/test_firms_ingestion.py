"""
Test FIRMS fire data ingestion module.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd


class TestFIRMSIngestion:
    """Test suite for FIRMS fire data ingestion."""

    def test_fetch_recent_fires_returns_dataframe(self):
        """Test that fetch_recent_fires returns a pandas DataFrame."""
        from src.data_ingestion.firms import fetch_recent_fires

        df = fetch_recent_fires(days=1)
        assert isinstance(df, pd.DataFrame), "Should return a DataFrame"

    def test_fetch_recent_fires_has_required_columns(self):
        """Test that DataFrame has all required columns."""
        from src.data_ingestion.firms import fetch_recent_fires

        df = fetch_recent_fires(days=1)

        required_columns = [
            'latitude', 'longitude', 'frp', 'brightness',
            'confidence', 'acq_date', 'acq_time', 'satellite'
        ]

        for col in required_columns:
            assert col in df.columns, f"Column {col} should exist"

    def test_fetch_recent_fires_with_bbox(self):
        """Test fetching fires for Indonesia bbox."""
        from src.data_ingestion.firms import fetch_recent_fires

        # Indonesia bbox
        df = fetch_recent_fires(days=1, bbox="95,-11,141,6")

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        # Check latitude/longitude are within bbox
        if len(df) > 0:
            assert df['latitude'].min() >= -11, "Latitude should be within bbox"
            assert df['latitude'].max() <= 6, "Latitude should be within bbox"
            assert df['longitude'].min() >= 95, "Longitude should be within bbox"
            assert df['longitude'].max() <= 141, "Longitude should be within bbox"

    def test_save_fires_to_database(self):
        """Test saving fire detections to database."""
        from src.data_ingestion.firms import fetch_recent_fires, save_fires_to_db
        from src.database import get_session, FireDetection

        # Fetch recent fires
        df = fetch_recent_fires(days=1)

        if len(df) == 0:
            pytest.skip("No fire data available for testing")

        # Save to database
        count = save_fires_to_db(df)
        assert count > 0, "Should save at least one record"

        # Verify in database
        session = get_session()
        fires = session.query(FireDetection).limit(10).all()
        session.close()

        assert len(fires) > 0, "Should have fire records in database"

    def test_parse_acquisition_datetime(self):
        """Test parsing FIRMS acquisition date and time."""
        from src.data_ingestion.firms import parse_acquisition_datetime

        # Test typical FIRMS format
        dt = parse_acquisition_datetime("2025-01-15", "1430")
        assert isinstance(dt, datetime), "Should return datetime"
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30

    def test_deduplicate_fires(self):
        """Test deduplication of fire records."""
        from src.data_ingestion.firms import deduplicate_fires

        # Create test DataFrame with duplicates
        test_data = pd.DataFrame([
            {'latitude': 1.5, 'longitude': 103.8, 'acq_date': '2025-01-15', 'acq_time': '1430', 'satellite': 'N20'},
            {'latitude': 1.5, 'longitude': 103.8, 'acq_date': '2025-01-15', 'acq_time': '1430', 'satellite': 'N20'},
            {'latitude': 2.0, 'longitude': 104.0, 'acq_date': '2025-01-15', 'acq_time': '1500', 'satellite': 'N20'},
        ])

        df = deduplicate_fires(test_data)
        assert len(df) == 2, "Should remove duplicates"
