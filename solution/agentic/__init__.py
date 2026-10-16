"""UDA-Hub multi-agent customer support system."""
import sys
from pathlib import Path

# Make `data.models` and `utils` importable no matter where the package is used from.
_STARTER_DIR = str(Path(__file__).resolve().parent.parent)
if _STARTER_DIR not in sys.path:
    sys.path.insert(0, _STARTER_DIR)
