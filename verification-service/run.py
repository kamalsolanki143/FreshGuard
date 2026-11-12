"""Production and development runner for FreshGuard Verification Service.

Dynamically binds to $PORT and $HOST provided by hosting platforms (e.g. Render,
Railway, Cloud Run) with sensible local fallbacks.
"""

import os
import uvicorn
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", settings.HOST)
    reload = settings.DEBUG and settings.ENVIRONMENT == "development"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
