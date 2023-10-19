# Test sequence. It can be deployed by si (then STH performs run() directly),
# or it can be started manually from CLI by `/bin/python main.py`
# (then asyncio runs run_without_sth())

# Test:
# si seq deploy ...; si inst output - > /dev/null &
# si inst stdout -

provides = {
   'contentType': 'application/octet-stream'
}

import asyncio
import glob
import time
import struct
import random

from os import system
from enum import Enum
from scramjet.streams import Stream
from serial_asyncio import open_serial_connection

#Regular expression to find MCU devices with UART
DEVICE_REGEXP = '/dev/ttyA??[0-9]*'

#Delay before start test. In seconds
START_DELAY_TIME = 3

#How long test should capturing data from MCUs. In seconds
TEST_DURATION_IN_SEC = 7250

#Number of required devices to start test, it stops otherwise. 
REQUIRED_DEVICES_TO_TEST = 10

#Single chunk size for read. In bytes.
CHUNK_SIZE = 128

#UART baudrate
BAUDRATE  = 115200 

#Print progress details during test on stdout or not?
ENABLE_PROGESS_LOGS = True

#How many times to show progress during whole test
PROGRESS_LOG_FREQUENCY = 50 

#List of required MCUs names
REQUIRED_MCU_NAMES = ['Pico#001', 'Pico#002', 'Pico#003', 'Pico#004',
                      'Pico#005', 'Pico#006', 'Pico#007', 'Pico#008',
                      'Pico#009', 'STM#000']

class ScramjetMCUProtocol:
    
    class _Commands(Enum):
            Ping = 0,
            Pong = 1,
            NameRequest = 2,
            NameResponse = 3,
            FloodOn = 4,
            FloodOff = 5,
            Input = 6,
            Output = 7,
            Error = 8,
            Undefined = 9 

    @staticmethod
    async def send_request(dev,command,param=None):
        
        writer = dev["writer"]        

        # requests with 2-byte param
        if command in [ScramjetMCUProtocol._Commands.Ping]:
            writer.write(struct.pack("!BH",command.value[0], param))
            await writer.drain()

        # requests without 2-byte param
        if command in [ScramjetMCUProtocol._Commands.NameRequest]:
            writer.write(struct.pack("!B", command.value[0]))
            await writer.drain()
               
        # requests without 2-byte param
        if command in [ScramjetMCUProtocol._Commands.FloodOn, ScramjetMCUProtocol._Commands.FloodOff]:
            writer.write(struct.pack("!B", command.value[0]))
            await writer.drain()
        
    @staticmethod
    async def get_response(dev):
        
        reader = dev['reader']
        try:
            command = ScramjetMCUProtocol._Commands(struct.unpack("!B", await asyncio.wait_for(reader.read(1),1)))
        except asyncio.TimeoutError:
            return ScramjetMCUProtocol._Commands.Error, 'Command waiting timeout'

        # response without 2-byte param, *without* size and payload
        if command in [ScramjetMCUProtocol._Commands.Pong]:
            return command, struct.unpack("!H",await reader.read(2))[0]
        
        # response without 2-byte param, *with* size and payload
        if command in [ScramjetMCUProtocol._Commands.NameResponse, ScramjetMCUProtocol._Commands.Error]:
            size = struct.unpack("!H",await reader.read(2))[0]
            payload = (struct.unpack( ("!%ds" % size), await reader.read(size))[0]).decode(encoding="ascii")
            return command, payload


class MCUManager:

    async def ping_device(self, dev):
        
        await self.flush_mcu_buffers(dev)

        ping_request = random.randint(0, 10)
        
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.Ping,ping_request)
        
        command, ping_response = await ScramjetMCUProtocol.get_response(dev)

        if command == ScramjetMCUProtocol._Commands.Pong and ping_request == ping_response:
            print(f'Device {dev["tty"]} OK')
            return True 
                     
        print(f'Ping failed. Device {dev["tty"]} returned an error: {ping_response}')
        return False


    async def identify_device(self, dev):
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.NameRequest)
            
        command, name = await ScramjetMCUProtocol.get_response(dev)
        
        if command == ScramjetMCUProtocol._Commands.NameResponse:
                dev['name'] = name
                self.mcu.append(dev)
                self.expected_mcus.remove(name)
                print(f'Device {dev["tty"]} identified as {dev["name"]}')
                return True

        print(f'Identify failed. Device {dev["tty"]} returned an error: {name}')
        return False


    async def close_connections(self):
        for dev in self.mcu:

            dev['writer'].close()
            await dev['writer'].wait_closed()
            print(f'Connection with device {dev["tty"]} closed')

    async def prepare_connections(self):
        
        #Kill descriptors, sometimes it helps :D
        for port in glob.glob(DEVICE_REGEXP):
            system(f'fuser -k {port}')
        
        time.sleep(1)

        for port in glob.glob(DEVICE_REGEXP):
            reader, writer = await open_serial_connection(url=port, baudrate=BAUDRATE)
            
            dev = {'reader': reader, 'writer': writer, 'tty' : port}
            
            if not await self.ping_device(dev):
                continue

            if not await self.identify_device(dev):
                continue
            
    def __init__(self, expected_mcus):
        
        self.stop_event = asyncio.Event()
        self.start_event = asyncio.Event()
        self.start_time = None
        self.expected_mcus = expected_mcus
        
        self.mcu = []
        self.throughput = {}

    @property
    def undetected_devices(self):
        return self.expected_mcus
    
    async def read_from_mcu(self, dev, stream):

        who = dev['name']
        self.throughput[who] = 0
        
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.FloodOn)
        print(f'{who}: Ready...')

        await self.start_event.wait()

        print(f'{who}: Start! ...Working...')
        while not self.stop_event.is_set():
            chunk = await dev['reader'].read(CHUNK_SIZE)
            self.throughput[who] = self.throughput[who] + len(chunk)
            stream.write(chunk)
            await asyncio.sleep(0)
        
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.FloodOff)
        await self.flush_mcu_buffers(dev)
    
    async def flush_mcu_buffers(self, dev, timeout=1):
        while True:
            try:
                chunk = await asyncio.wait_for(dev['reader'].read(CHUNK_SIZE),timeout)
                if not chunk:
                    break
            except asyncio.TimeoutError:
                break

async def _progress(manager, duration):
    from datetime import datetime

    await manager.start_event.wait()
    while not manager.stop_event.is_set():

        print(f'--- Time: {datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")} UTC ---')
        print(f'--- Progress: { int(100*(duration - int((manager.start_time + duration) - time.time()))/duration)} % ---') 
        print('')
        await asyncio.sleep(duration/PROGRESS_LOG_FREQUENCY)
        

async def _watchdog(manager, stream, duration):

    print(f'Watchog is waiting {START_DELAY_TIME} seconds before start!')
    
    await asyncio.sleep(START_DELAY_TIME)        

    manager.start_event.set()
    manager.start_time = time.time()
    start_time_struct = time.gmtime(manager.start_time)
    print(f'Start time: {start_time_struct.tm_year}-{start_time_struct.tm_mon}-{start_time_struct.tm_mday} {start_time_struct.tm_hour}:{start_time_struct.tm_min}:{start_time_struct.tm_sec} UTC')

    await asyncio.sleep(duration)

    manager.stop_event.set()

    end_time_struct = time.gmtime(time.time())
    print(f'End time: {end_time_struct.tm_year}-{end_time_struct.tm_mon}-{end_time_struct.tm_mday} {end_time_struct.tm_hour}:{end_time_struct.tm_min}:{end_time_struct.tm_sec} UTC')
    
    print(f'Bytes per device: {manager.throughput}')
    total = 0
    for el in manager.throughput.values():
        total += el
    print(f'Total throughput: { (total * 8 ) / 1024 / TEST_DURATION_IN_SEC } kbps')
    
    await asyncio.sleep(2)

    stream.end()

async def run(context, input, *args) -> Stream:

    stream = Stream()
    manager = MCUManager(REQUIRED_MCU_NAMES)

    await manager.prepare_connections()
    
    if len(manager.mcu) != REQUIRED_DEVICES_TO_TEST:
        print(f'Number of detected MCUs: {len(manager.mcu)}. It is less than required {REQUIRED_DEVICES_TO_TEST}')
        print(f'Undetected devices: {manager.undetected_devices}')

        await manager.close_connections()
        stream.write(b'')
        stream.end()
        return stream
        
    background_tasks = set()

    for dev in manager.mcu:

        task = asyncio.create_task(manager.read_from_mcu(dev,stream))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    asyncio.create_task(_watchdog(manager, stream, TEST_DURATION_IN_SEC))
    
    if ENABLE_PROGESS_LOGS:
        asyncio.create_task(_progress(manager, TEST_DURATION_IN_SEC))

    return stream

async def run_without_sth():
    async for item in await run(context=None,input=None):
        pass 

if __name__ == "__main__":
    asyncio.run(run_without_sth())

