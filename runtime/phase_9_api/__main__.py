"""Run API: python -m runtime.phase_9_api"""

from __future__ import annotations

import sys

import uvicorn

from phases.common.env import load_project_env
from runtime.phase_9_api.config import load_api_config

load_project_env()


def main() -> int:
    cfg = load_api_config()
    uvicorn.run(
        "runtime.phase_9_api.app:app",
        host=cfg.host,
        port=cfg.port,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
