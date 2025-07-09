import asyncio
import logging
from src.exchanges.deribit_options import deribit_options

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    # Simulate a spot position
    spot_qty = 1.0
    logger.info(f"Simulated spot position: {spot_qty} BTC")

    # Fetch available expiries for BTC puts
    logger.info("Fetching Deribit instruments...")
    async with deribit_options:
        instruments = await deribit_options.get_instruments()
        logger.info(f"Fetched {len(instruments)} instruments.")
        put_instruments = [
            i
            for i in instruments
            if i.symbol.startswith("BTC")
            and i.instrument_type == "option"
            and "-P" in i.symbol
        ]
        logger.info(f"Filtered to {len(put_instruments)} BTC put options.")
        expiries = sorted(list(set(i.symbol.split("-")[1] for i in put_instruments)))
        logger.info(f"Available expiries: {expiries}")
        # Pick the first expiry
        if not expiries:
            logger.error("No expiries found!")
            return
        expiry = expiries[0]
        logger.info(f"Testing strikes for expiry: {expiry}")
        puts_for_expiry = [
            i for i in put_instruments if i.symbol.split("-")[1] == expiry
        ]
        logger.info(f"Found {len(puts_for_expiry)} puts for expiry {expiry}.")
        strikes = sorted(
            list(set(float(i.symbol.split("-")[2]) for i in puts_for_expiry))
        )
        logger.info(f"Available strikes for {expiry}: {strikes}")
        for inst in puts_for_expiry[:5]:
            logger.info(f"Instrument: {inst.symbol}")


if __name__ == "__main__":
    asyncio.run(main())
