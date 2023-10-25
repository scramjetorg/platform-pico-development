import asyncio
from scramjet.streams import Stream


async def read_input(input, output):
    async for chunk in input:
        if chunk != b'':
            output.write(chunk)


async def run(context, input, *args) -> Stream:
    output = Stream()
    asyncio.create_task(read_input(input, output))

    return output
