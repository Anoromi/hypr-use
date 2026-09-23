"""Run the pinned portal's isolated AT-SPI operation with runtime fixes."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from runtime_fixes import install


root = Path(__file__).resolve().parents[2]
source = root / "vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py"
spec = importlib.util.spec_from_file_location("hypr_use_atspi_child", source)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load pinned portal backend: {source}")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
install(backend)

if len(sys.argv) != 2 or sys.argv[1] not in backend.ATSPI_CHILD_MODES:
    raise SystemExit("expected one AT-SPI child mode")
raise SystemExit(backend.atspi_child_main(sys.argv[1]))
