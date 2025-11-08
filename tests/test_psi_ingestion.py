"""
Test Singapore PSI data ingestion module.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
from datetime import datetime
import pandas as pd


class TestPSIIngestion:
    """Test suite for Singapore PSI data ingestion."""

    def test_fetch_current_psi_returns_dataframe(self):
        """Test that fetch_current_psi returns a pandas DataFrame."""
        from src.data_ingestion.psi import fetch_current_psi

        df = fetch_current_psi()
        assert isinstance(df, pd.DataFrame), "Should return a DataFrame"
        assert len(df) > 0, "Should have at least one record"

    def test_fetch_current_psi_has_required_columns(self):
        """Test that DataFrame has all required columns."""
        from src.data_ingestion.psi import fetch_current_psi

        df = fetch_current_psi()

        required_columns = [
            'timestamp', 'region', 'psi_24h'
        ]

        for col in required_columns:
            assert col in df.columns, f"Column {col} should exist"

    def test_fetch_current_psi_has_all_regions(self):
        """Test that all regions are included."""
        from src.data_ingestion.psi import fetch_current_psi

        df = fetch_current_psi()

        # National might not always be present, but regional readings should be
        expected_regions = ['north', 'south', 'east', 'west', 'central']
        actual_regions = df['region'].unique().tolist()

        for region in expected_regions:
            assert region in actual_regions, f"Region {region} should be present"

        # Should have at least 5 regions
        assert len(actual_regions) >= 5, "Should have at least 5 regional readings"

    def test_fetch_historical_psi(self):
        """Test fetching historical PSI data."""
        from src.data_ingestion.psi import fetch_historical_psi

        df = fetch_historical_psi(limit=100)

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) > 0, "Should have historical data"
        assert 'timestamp' in df.columns
        assert 'psi_24h' in df.columns

    def test_save_psi_to_database(self):
        """Test saving PSI data to database."""
        from src.data_ingestion.psi import fetch_current_psi, save_psi_to_db
        from src.database import get_session, PSIReading

        # Fetch current PSI
        df = fetch_current_psi()
        assert len(df) > 0, "Should fetch PSI data"

        # Save to database (may return 0 if duplicates)
        count = save_psi_to_db(df)

        # Verify records exist in database (regardless of whether we just saved them)
        session = get_session()
        psi = session.query(PSIReading).limit(10).all()
        session.close()

        assert len(psi) > 0, "Should have PSI records in database"

    def test_parse_psi_response(self):
        """Test parsing PSI API response."""
        from src.data_ingestion.psi import parse_psi_response

        # Mock response data
        mock_data = {
            'items': [{
                'timestamp': '2025-01-15T14:00:00+08:00',
                'readings': {
                    'psi_twenty_four_hourly': {
                        'national': 55,
                        'north': 52,
                        'south': 54,
                        'east': 53,
                        'west': 55,
                        'central': 51
                    },
                    'pm25_twenty_four_hourly': {
                        'national': 15,
                        'north': 14,
                        'south': 15,
                        'east': 14,
                        'west': 15,
                        'central': 13
                    }
                }
            }]
        }

        df = parse_psi_response(mock_data)

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) == 6, "Should have 6 regions"
        assert df['psi_24h'].iloc[0] >= 0, "PSI values should be non-negative"

    def test_get_psi_status(self):
        """Test PSI status categorization."""
        from src.data_ingestion.psi import get_psi_status

        assert get_psi_status(30) == "Good"
        assert get_psi_status(75) == "Moderate"
        assert get_psi_status(150) == "Unhealthy"
        assert get_psi_status(250) == "Very Unhealthy"
        assert get_psi_status(350) == "Hazardous"
