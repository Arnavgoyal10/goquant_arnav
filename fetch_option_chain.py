import asyncio
from src.exchanges.deribit_options import deribit_options


async def main():
    print("Fetching BTC option instruments from Deribit...")
    async with deribit_options:
        instruments = await deribit_options.get_instruments()
        btc_options = [
            i
            for i in instruments
            if i.symbol.startswith("BTC") and i.instrument_type == "option"
        ]
        print(f"Found {len(btc_options)} BTC option instruments.")
        for inst in btc_options[:10]:
            print(
                f"{inst.symbol} | Type: {inst.instrument_type} | Exchange: {inst.exchange}"
            )


if __name__ == "__main__":
    asyncio.run(main())
