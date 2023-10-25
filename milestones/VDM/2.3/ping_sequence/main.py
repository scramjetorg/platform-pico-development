import time
from scramjet.streams import Stream
import asyncio
import uuid
import aiohttp

STH_INSTANCE_INPUT_URL = "http://127.0.0.1:8000/api/v1/instance/6dd0e6aa-94da-420f-a67f-6df2a6706912/input"
STH_INSTANCE_OUTPUT_URL = "https://889c219f-04e5-4ac0-9268-dafa9fe6d2e0.mock.pstmn.io"
SEND_DELAY_S = 1

keep_working = asyncio.Event()


async def generate_payload():
    while not keep_working.is_set():
        payload = str({'id': str(uuid.uuid4())}) + '\n'
        yield payload.encode(encoding="utf-8")
        await asyncio.sleep(SEND_DELAY_S)

async def send_id(send_timestamps: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(STH_INSTANCE_INPUT_URL, data=generate_payload(), headers={'Content-Type': 'text/plain'}) as resp:
            print(resp.status)
            print(await resp.text())


async def read_input(seq_input: Stream, send_timestamps: dict, results_stream: Stream):
    while keep_working:
        body = await seq_input.read()
        received_time = time.time()
        send_time = send_timestamps.get(body.id, None)
        if send_time is None:
            continue
        round_trip = received_time - send_time
        results_stream.write(round_trip)


async def run(context, input, *args) -> Stream:
    global keep_working
    results_stream = Stream()
    send_timestamps = dict()

    task1 = asyncio.create_task(send_id(send_timestamps))
    # task2 = asyncio.create_task(read_input(input, send_timestamps))

    await asyncio.sleep(4)

    keep_working.set()
    results_stream.end()

    return results_stream


async def run_without_sth():
    async for item in await run(context=None, input=None):
        print(item)


if __name__ == "__main__":
    asyncio.run(run_without_sth())
