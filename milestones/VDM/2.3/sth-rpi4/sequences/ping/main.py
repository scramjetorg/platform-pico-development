import time
from scramjet.streams import Stream
import asyncio
import uuid
import aiohttp
import json
import datetime
from statistics import mean

HOST = "192.168.0.5"
STH_INSTANCE_INPUT_URL = f"http://{HOST}:8000/api/v1/instance/6dd0e6aa-94da-420f-a67f-6df2a6706912/input"
STH_INSTANCE_OUTPUT_URL = f"http://{HOST}/api/v1/instance/6dd0e6aa-94da-420f-a67f-6df2a6706912/output"
SEND_DELAY_S = 1
TEST_DURATION = 2 * 60 * 60

keep_working = asyncio.Event()
round_trips = []


async def generate_payload(send_id_time: dict):
    while not keep_working.is_set():
        id = str(uuid.uuid4())
        payload = json.dumps({'id': id}) + "\n"
        send_id_time[id] = time.time()
        yield payload.encode(encoding="utf-8")
        await asyncio.sleep(SEND_DELAY_S)


async def send_id(session: aiohttp.ClientSession, send_id_time: dict):
    async with session.post(STH_INSTANCE_INPUT_URL, data=generate_payload(send_id_time), headers={'Content-Type': 'text/plain'}) as resp:
        await resp.text()


async def receive_id(session: aiohttp.ClientSession, send_id_time:dict, results_stream: Stream):
    chunk = bytes()
    async with session.get(STH_INSTANCE_OUTPUT_URL) as resp:
        async for data, endOfChunk in resp.content.iter_chunks():
            chunk += data
            if not endOfChunk:
                continue
            receive_time = time.time()
            try:
                id = json.loads(chunk)["id"]
                count_chunk_roundtrip(id, receive_time, send_id_time, results_stream)
            except Exception as e:
                print(e)
            chunk = bytes()


def count_chunk_roundtrip(id, receive_time, send_id_time: dict, results_stream: Stream):
    send_time = send_id_time.get(id, None)
    if send_time == None:
        print(f"Id: ${id} not found")
    t1 = datetime.datetime.fromtimestamp(send_time)
    t2 = datetime.datetime.fromtimestamp(receive_time)
    round_trip_time = t2 -t1 
    ms = round_trip_time.total_seconds() * 1000
    round_trips.append(ms)
    results_stream.write(f"Roundtrip is {ms:3.3f} milliseconds avg: {mean(round_trips):3.3f}")


async def watchdog(session, results_stream):
    await asyncio.sleep(TEST_DURATION)
    keep_working.set()                                 
    await session.close()
    results_stream.end()


async def run(context, input, *args) -> Stream:
    global keep_working
    results_stream = Stream()
    send_id_time = dict()
    session = aiohttp.ClientSession()

    asyncio.create_task(watchdog(session, results_stream))
    asyncio.create_task(send_id(session, send_id_time))
    asyncio.create_task(receive_id(session, send_id_time, results_stream))

    return results_stream


async def run_without_sth():
    async for item in await run(context=None, input=None):
        print(item)


if __name__ == "__main__":
    asyncio.run(run_without_sth())
