"""
Baseline PSI score calculation.
Normalizes current PSI to 0-100 scale.
"""


def calculate_baseline_score(current_psi):
    """
    Normalize current PSI to 0-100 scale.

    Implements the algorithm from TDD.md:
    - PSI can theoretically exceed 500 during extreme events
    - Cap at 500 for normalization
    - Divide by 5.0 to get 0-100 scale

    Args:
        current_psi: Current PSI value from NEA API

    Returns:
        float: Baseline score 0-100
    """
    # Handle negative or invalid values
    if current_psi < 0:
        return 0.0

    # Cap at 500 and normalize
    baseline_score = min(current_psi, 500) / 5.0

    return baseline_score
