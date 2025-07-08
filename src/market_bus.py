"""Market data bus that merges streams from multiple exchanges."""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
from loguru import logger

from .exchanges.okx import OKXExchange
from .exchanges.deribit import DeribitExchange


class MarketBus:
    """Market data bus that aggregates data from multiple exchanges."""

    def __init__(self):
        self.queue = asyncio.Queue()
        self.exchanges = {"OKX": OKXExchange(), "Deribit": DeribitExchange()}
        self.running = False

    async def start(self):
        """Start the market bus."""
        self.running = True
        logger.info("Starting market bus...")

        # Start all exchange streams
        tasks = []
        for name, exchange in self.exchanges.items():
            task = asyncio.create_task(self._stream_exchange(name, exchange))
            tasks.append(task)

        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop the market bus."""
        self.running = False
        logger.info("Stopping market bus...")

    async def _stream_exchange(self, name: str, exchange):
        """Stream data from a single exchange."""
        async with exchange:
            async for timestamp, symbol, bid, ask in exchange.stream():
                if not self.running:
                    break

                # Put data in the queue
                await self.queue.put((timestamp, symbol, bid, ask))
                logger.debug(f"{name} {symbol}: {bid} / {ask}")

    async def get_next(self) -> tuple[datetime, str, float, float]:
        """Get the next market data update.

        Returns:
            Tuple of (timestamp, symbol, bid, ask)
        """
        return await self.queue.get()

    def get_queue_size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()


async def smoke_test():
    """Run a 60-second smoke test of the market bus."""
    logger.info("Starting 60-second smoke test...")

    market_bus = MarketBus()

    # Start the market bus in the background
    bus_task = asyncio.create_task(market_bus.start())

    # Collect data for 60 seconds
    updates = []
    start_time = datetime.now()

    try:
        while (datetime.now() - start_time).total_seconds() < 60:
            try:
                # Wait for next update with timeout
                update = await asyncio.wait_for(market_bus.get_next(), timeout=15.0)
                updates.append(update)
                timestamp, symbol, bid, ask = update
                logger.info(f"Update: {timestamp} {symbol} {bid:.2f} / {ask:.2f}")
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for market data")
                break
    finally:
        # Stop the market bus
        await market_bus.stop()
        bus_task.cancel()

    logger.info(f"Smoke test complete. Collected {len(updates)} updates.")
    return updates


if __name__ == "__main__":
    # Run smoke test
    asyncio.run(smoke_test())
