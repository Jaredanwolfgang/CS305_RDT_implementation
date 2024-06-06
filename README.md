# RDT Implementation

For the socket package, we can only use the method for UDP, which is `recvfrom()` and `sendto()`. 
We need to use threads to maintain a "connection" between the client and the server, because the server needs to be able to handle multiple clients at once.
Each socket is binded to an address and a port, while connecting to a server, the client needs to know the address and the port of the server.
After the server gets the address and the port of the client, it will maintain a FSM with the according client to form a "connection".

## Usage
There are in total three test files that should be run to test the realization and performance of the RDT implementation.
1. `test_case.py` is the test file for the basic realization of the RDT implementation.
2. `calculate_throughput.py` is the test file for the large file transmission performance of the RDT implementation.
3. `calculate_latency.py` is the test file for the latency of the RDT implementation.

The first one requires modifying the `LOCAL_IP` field based on the current IP address.(Please ensure that it is connected with the campus network) The last two files are run locally. 

## File structure
There are in total 11 files in the repository:
```shell
  .
  ├── calculate_latency.py # calculate the latency of the RDT implementation
  ├── calculate_throughput.py # calculate the throughput of the RDT implementation
  ├── congestion.py # the congestion control module
  ├── data  # the data folder for the test files
  │    ├── original.txt
  │    ├── transmit_rdt.txt
  │    └── transmit_udp.txt
  ├── Header.py # the RDTHeader
  ├── proxy.py # the proxy server for the test files
  ├── RDT.py # the RDT implementation
  ├── README.md # the README file
  └── test_case.py # the test file for the basic realization of the RDT implementation
```

## Realization
### Connection
- [x] 3-way Handshake
- [x] 4-way Handshake
- [x] Multithreading

### Packet Verfiication
- [x] Checksum Generate
- [x] Checksum in `send()`
- [x] Checksum in `recv()`

### Retransmitting
- [x] FSM for basic `send()` and `recv()` 

### Data Segmentation
- [x] Segmenting data into packets
- [x] Reassembling packets into data

### Congestion Control
- [x] Slow Start
- [x] Congestion Avoidance
- [x] Fast Retransmit
- [x] Fast Recovery

### Flow Control
- [x] Sliding Window
- [x] Selective Repeat
- [ ] Go-Back-N

### Error Control
- [x] Error Detection
- [ ] Error Correction
- [ ] Error Recovery

### Performance Improvement
- [x] Pipelining

## Further Improvement
After communicating with our SAs and other classmates, there are some places we can improve the final performance.
1. Use multiprocess instead of multithread. In python version `3.9`, threading is actually running within only one thread, which will not bring much improvement.
2. Try to send and receive data from the same process. Because the socket in python can only be run within one thread or process, there are large time penalty when switching the socket connection between differen threads.
3. Use queue to demultiplex data. In our realization, we use list to store the incoming data. It is neither thread-safe nor blocking, which might cost a performance loss.
