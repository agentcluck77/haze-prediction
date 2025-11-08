"""
Test baseline PSI score calculation.
Following TDD protocol: Write tests first, then implement.
"""

import pytest


class TestBaselineScore:
    """Test suite for baseline PSI score calculation."""

    def test_calculate_baseline_score_zero_psi(self):
        """Test that PSI of 0 gives baseline score of 0."""
        from src.features.baseline import calculate_baseline_score

        score = calculate_baseline_score(0)
        assert score == 0, "PSI 0 should give baseline score 0"

    def test_calculate_baseline_score_normal_range(self):
        """Test baseline score for typical PSI values."""
        from src.features.baseline import calculate_baseline_score

        # PSI 50 (Good) -> Score 10
        assert calculate_baseline_score(50) == pytest.approx(10.0, abs=0.1)

        # PSI 100 (Moderate) -> Score 20
        assert calculate_baseline_score(100) == pytest.approx(20.0, abs=0.1)

        # PSI 200 (Unhealthy) -> Score 40
        assert calculate_baseline_score(200) == pytest.approx(40.0, abs=0.1)

    def test_calculate_baseline_score_high_psi(self):
        """Test baseline score for high PSI values."""
        from src.features.baseline import calculate_baseline_score

        # PSI 300 (Very Unhealthy) -> Score 60
        assert calculate_baseline_score(300) == pytest.approx(60.0, abs=0.1)

        # PSI 500 (Hazardous) -> Score 100
        assert calculate_baseline_score(500) == pytest.approx(100.0, abs=0.1)

    def test_calculate_baseline_score_capped_at_100(self):
        """Test that baseline score is capped at 100."""
        from src.features.baseline import calculate_baseline_score

        # PSI > 500 should still cap at 100
        assert calculate_baseline_score(600) == 100
        assert calculate_baseline_score(1000) == 100

    def test_calculate_baseline_score_range(self):
        """Test that baseline score is always 0-100."""
        from src.features.baseline import calculate_baseline_score

        for psi in [0, 25, 50, 100, 150, 200, 300, 500, 1000]:
            score = calculate_baseline_score(psi)
            assert 0 <= score <= 100, f"Score for PSI {psi} should be 0-100, got {score}"

    def test_calculate_baseline_score_negative_psi(self):
        """Test that negative PSI is treated as 0."""
        from src.features.baseline import calculate_baseline_score

        score = calculate_baseline_score(-10)
        assert score == 0, "Negative PSI should give baseline score 0"
