"""
Check-in metrics validation.

Validates check-in metric values against allowed ranges.
"""

from typing import Tuple, Optional, Dict, Any


class MetricsValidator:
    """
    Validates check-in metric values against allowed ranges.
    """

    METRIC_RANGES: Dict[str, Tuple[int, int]] = {
        "mood": (1, 5),
        "physicalEnergy": (1, 10),
        "mentalEnergy": (1, 10),
        "sleep": (1, 5),
        "stress": (1, 10),
    }

    REQUIRED_METRICS = ["mood", "physicalEnergy", "mentalEnergy", "sleep", "stress"]

    MAX_NOTES_LENGTH = 500

    @classmethod
    def validate(cls, metrics: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate all metrics are present and within valid ranges.

        Args:
            metrics: dict with metric values

        Returns:
            tuple of (is_valid, error_message)
        """
        for metric in cls.REQUIRED_METRICS:
            if metric not in metrics:
                return False, f"Missing required field: {metric}"

            value = metrics[metric]

            if not isinstance(value, int):
                return False, f"Field '{metric}' must be an integer"

            min_val, max_val = cls.METRIC_RANGES[metric]
            if value < min_val or value > max_val:
                return False, f"Field '{metric}' must be between {min_val} and {max_val}"

        return True, None

    @classmethod
    def validate_notes(cls, notes: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate optional notes field.

        Args:
            notes: Optional notes string

        Returns:
            tuple of (is_valid, error_message)

        Rules:
            - Max 500 characters
            - Trimmed whitespace
        """
        if notes is None:
            return True, None

        if not isinstance(notes, str):
            return False, "Notes must be a string"

        trimmed = notes.strip()
        if len(trimmed) > cls.MAX_NOTES_LENGTH:
            return False, f"Notes cannot exceed {cls.MAX_NOTES_LENGTH} characters"

        return True, None
