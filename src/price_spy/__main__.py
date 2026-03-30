"""Entry point: python -m price_spy"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("price-spy starting...")
    # Will be wired in Plan 04


if __name__ == "__main__":
    asyncio.run(main())
