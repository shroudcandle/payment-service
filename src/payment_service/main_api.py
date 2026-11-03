from __future__ import annotations

import uvicorn

from payment_service.config import Settings, configure_logging


def main() -> None:
    settings = Settings()
    configure_logging(settings.app.log_level)
    uvicorn.run(
        "payment_service.presentation.api.app:create_app",
        factory=True,
        host=settings.app.api_host,
        port=settings.app.api_port,
        log_level=settings.app.log_level.lower(),
        log_config=None,
    )


if __name__ == "__main__":
    main()
