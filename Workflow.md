# RDT Implementation

For the socket package, we can only use the method for UDP, which is `recvfrom()` and `sendto()`. 
We need to use threads to maintain a "connection" between the client and the server, because the server needs to be able to handle multiple clients at once.
Each socket is binded to an address and a port, while connecting to a server, the client needs to know the address and the port of the server.
After the server gets the address and the port of the client, it will maintain a FSM with the according client to form a "connection".

## Connection
[ ] 3-way Handshake
[ ] 4-way Handshake
[ ] Multithreading

## Packet Verfiication
[*] Checksum Generate
[ ] Checksum in `send()`
[ ] Checksum in `recv()`

## Retransmitting
[ ] FSM for basic `send()` and `recv()` 

## Data Segmentation
[ ] Segmenting data into packets
[ ] Reassembling packets into data

## Congestion Control
[ ] Slow Start
[ ] Congestion Avoidance
[ ] Fast Retransmit
[ ] Fast Recovery

## Flow Control
[ ] Sliding Window
[ ] Selective Repeat
[ ] Go-Back-N

## Error Control
[ ] Error Detection
[ ] Error Correction
[ ] Error Recovery

## Performance Improvement
[ ] Pipelining