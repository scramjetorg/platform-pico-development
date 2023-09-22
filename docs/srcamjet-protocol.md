# Scramjet protocol

|   Name   | Direction | Byte[0] | Byte[1-2] | Payload |
|:--------:|:---------:|:-------:|:---------:|:-------:|
|   Ping   |  Request  |   0x0   |     id    |    No   |
|   Pong   |  Response |   0x1   |     id    |    No   |
|  NameReq |  Request  |   0x2   |     -     |    No   |
|  NameRes |  Response |   0x3   |    size   |   Yes   |
|  FloodOn |  Request  |   0x4   |     -     |    No   |
| FloodOff |  Request  |   0x5   |     -     |    No   |
|   Input  |  Request  |   0x6   |    size   |   Yes   |
|  Output  |  Response |   0x7   |    size   |   Yes   |
|   Error  |  Response |   0x8   |    size   |   Yes   |

- Ping/Pong - check alive status, id in Pong response should return same id as Ping Request. Example:\
Ping: `0x0 0x17`\
Pong: `0x1 0x17`

- NameReq/NameRes - check board sequence name. Payload is coded as `char*` of `size` in header without `nullbyte`. Example:\
NameReq: `0x2`\
NameRes: `0x3 0x08 S C R A M J E T`

- FloodOn/FloodOff - start/stop generating constant data over time. Example:\
FloodOn: `0x4`\
FloodOff: `0x5`

- Input - send data into the user sequence. Example:\
`0x7 0x08 0x53 0x43 0x52 0x41 0x4D 0x4A 0x45 0x54` 

- Output - sent data from user sequence Example:\
`0x8 0x08 0x53 0x43 0x52 0x41 0x4D 0x4A 0x45 0x54` 

- Error - error message. Payload is coded as `char*` of `size` in header without `nullbyte`. Example:\
`0x8 0x10 U n k n o w n  c m d _ c o d e`
