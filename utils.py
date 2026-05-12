"""Utility functions for color manipulation and common helpers."""

import colorsys
from typing import Tuple
from PySide6.QtGui import QColor


def bob_hue(index: int, total: int) -> float:
    """Generate a visually distinct hue using golden ratio distribution."""
    return (index * 0.618033988749895) % 1.0


def bob_qcolor(index: int, total: int) -> QColor:
    """Generate a vibrant color for bob at given index."""
    h = bob_hue(index, total)
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return QColor(int(r * 255), int(g * 255), int(b * 255))


def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linearly interpolate between two colors."""
    t = max(0.0, min(1.0, t))  # Clamp t to valid range
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def is_valid_position(x: float, y: float) -> bool:
    """Check if a position contains valid finite coordinates."""
    import math
    return math.isfinite(x) and math.isfinite(y)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))