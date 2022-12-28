import asyncio

from websockets import serve

from ekiden.relay import handler


async def main():
    async with serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
