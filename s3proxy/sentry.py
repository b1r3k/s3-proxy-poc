import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration

from .config import settings
from .logging import root_logger

logger = root_logger.getChild(__name__)


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="url"),
        ],
    )
else:
    logger.warning("No SENTRY_DSN set, Sentry integration disabled")
