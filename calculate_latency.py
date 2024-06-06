import socket
import os
import threading
import time
import queue
from multiprocessing import Process
from RDT import RDTSocket as RDTSocket
from  Header import RDTHeader

Speed_RDT = 0
Speed_UDP = 0

source_address = ('127.0.0.1', 12334)
target_address = ('127.0.0.1', 12335)

def UDP_send(ip, port):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (ip, port)
    try:
        for i in range(0, 100):
            sock.sendto(str(float(time.time() * 1000)).encode(), server_address)
        # sock.sendto(str(float(time.time() * 1000)).encode(), server_address)
        sock.sendto('end'.encode(), server_address)
    except IOError as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()

def UDP_receive(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    spend_time = 0
    time_list = []
    try:
        while True:
            data, addr = sock.recvfrom(200)
            # spend_time = float(time.time() * 1000) - float(data.decode())
            # print(spend_time)
            if data == b'end':
                break
            else:
                spend_time = float(time.time() * 1000) - float(data.decode())
                time_list.append(spend_time)
        time_list.sort()
        print(f"{time_list[49]}")
    except IOError as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()

    print(f"UDP lantency : {spend_time} ms")

def UDP_start_test(port=12349):
    sender = Process(target=UDP_send, args=("localhost", port))
    receiver = Process(target=UDP_receive, args=("localhost", port))

    receiver.start()
    time.sleep(5)

    sender.start()

    sender.join()
    receiver.join()  
    


def RDT_start_test():
    sender = Process(target=RDT_send, args=(source_address, ("127.0.0.1", 12346)))
    receiver = Process(target=RDT_receive, args=(source_address,))

    receiver.start()
    time.sleep(2)
    sender.start()

    sender.join()
    receiver.join()


def RDT_send(source_address, target_address):
    """
        You need to send the system's timestamp and use it to calculate the latency of a communication. The following code is
        a reference code that you can modify due to differences in implementation. 

        Note that the lantency is calculated between the time the sender calls the function send() to send data and the time the receiver calls the function recv().
        params: 
            target_address:    Target IP address and its port
            source_address:    Source IP address and its port
    """
    #############################################################################
    # HINT: Since the lantency test could be finished locally. So you could
    #       assign the ProxyServerAddress as your true target address directly.
    #       you can change this code base on your implementation.
    #############################################################################
    client = RDTSocket()
    client.bind(target_address)
    client.isLocalTest = True
    client.listen(5)
    client.connect(source_address)
    print("Client Connect")
    client.send(source_address, data=str(float(time.time() * 1000)))
    print(f"Client connected to {source_address}")
    client.close()

def RDT_receive(source_address):
    """
        Depending on your design, you need to save the received data to flie_path. Make sure the data order is correct and the data is complete.
        Additionally, you need to time this process, starting from when the receiver receives the first piece of data until the receiver closes the connection.
        In order to reduce the impact of hardware, You can process all the data in memory. Writes to the hard disk (file path) after the connection is closed, which
        means the time overhead of writing data from memory to the hard disk is not counted.

        Please note that this experiment should be finished locally. So you could
        set the ProxyServerAddress of your RDTSocket as your true destination, rather
        than the adress of proxy_server.

        You can refer to function UDP_receive_file to complete this code.
        params:
            target_address:    Target IP address and its port
            source_address:    Source IP address and its port
            file_path:         The file path to the received data
    """
    # global recv_queue
    global data_received
    server = RDTSocket()
    server.bind(source_address)
    server.isLocalTest = True
    server.listen(5)
    while True:
        try:
            addr = server.accept()
            print("Connected to ", addr)
            data_received = server.recv(address=addr, test_case=0)
            print(data_received)
            break
        except KeyboardInterrupt:
            break
        except:
            continue

    spend_time = float(time.time() * 1000) - float(data_received[0])
    print(f"RDT lantency: {spend_time} ms")
    server.close()
    return

def test_latency():
    # UDP
    try:
        UDP_start_test()
    except Exception as e:
        print(e)

    # RDT
    try:
        RDT_start_test()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    test_latency()
    
