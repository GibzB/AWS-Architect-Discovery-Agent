"""AWS Lambda handler — wraps FastAPI with Mangum for API Gateway."""

import sys
from pathlib import Path

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
