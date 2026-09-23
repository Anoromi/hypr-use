"""Package entry point for the Python portal backend."""
import os
import sys
from pathlib import Path

backend = Path(__file__).with_name("backend.py")
os.execv(sys.executable, [sys.executable, str(backend)])
