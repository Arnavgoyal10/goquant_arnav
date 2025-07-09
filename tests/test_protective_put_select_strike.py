import asyncio
from src.exchanges.deribit_options import deribit_options


async def main():
    expiry = "11JUL25"  # Example expiry
    print(f"Testing strike extraction for expiry: {expiry}")
    async with deribit_options:
        instruments = await deribit_options.get_instruments()
        print(f"Total instruments: {len(instruments)}")
        put_instruments = [
            i
            for i in instruments
            if i.symbol.startswith("BTC")
            and i.instrument_type == "option"
            and "-P" in i.symbol
            and i.symbol.split("-")[1] == expiry
        ]
        print(f"Found {len(put_instruments)} puts for expiry {expiry}")
        strikes = sorted(
            list(set(float(i.symbol.split("-")[2]) for i in put_instruments))
        )
        print(f"Strikes: {strikes}")
        for inst in put_instruments[:5]:
            print(f"{inst.symbol}")


if __name__ == "__main__":
    asyncio.run(main())
