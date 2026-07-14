"""Pytest configuration — ensure imports work."""

import sys
from pathlib import Path

# Add project paths so agents/ and packages/ are importable
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))
