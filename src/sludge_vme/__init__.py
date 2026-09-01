"""Research-only sludge fired-brick virtual materials engine."""

from .config import load_case
from .models import simulate

__all__ = ["load_case", "simulate"]
__version__ = "0.1.0"
