import signal
import socket
import os
import time
import queue
from RDT import RDTSocket
from multiprocessing import Process

Speed_RDT = 0
Speed_UDP = 0


def UDP_send_file(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (ip, port)
    file_path = './original.txt'
    data_list = []
    try:
        with open(file_path, "rb") as file:
            data = file.read(256)
            while data:
                data_list.append(data)
                data = file.read(256)

        file.close()

        for i in data_list:
            sock.sendto(i, server_address)
        print(len(data_list))
        sock.sendto('end'.encode(), server_address)

    finally:
        sock.close()


def UDP_receive_file(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    save_path = './transmit_udp.txt'
    flag = True
    try:
        data_list = []
        while True:
            data, addr = sock.recvfrom(298)
            if flag:
                start_time = time.time()
                flag = False
            if data == b'end':
                break

            data_list.append(data)

        end_time = time.time()
        print(f"Using UDP file complete: {end_time - start_time} s")
        Speed_UDP = end_time - start_time

        with open(save_path, "wb") as file:
            for i in data_list:
                file.write(i)
    finally:
        sock.close()


def UDP_start_test(port=12349):
    sender = Process(target=UDP_send_file, args=("127.0.0.1", port))
    receiver = Process(target=UDP_receive_file, args=("127.0.0.1", port))

    receiver.start()
    time.sleep(5)

    sender.start()

    sender.join()
    receiver.join()


def RDT_start_test(port_source=12345, port_target=12346):
    sender = Process(target=RDT_send_file, args=(("10.27.40.212", port_source), ("10.27.40.212", port_target)))
    receiver = Process(target=RDT_receive_file, args=(("10.27.40.212", port_source), ("10.27.40.212", port_target)))

    receiver.start()
    time.sleep(5)
    sender.start()

    sender.join()
    receiver.join()


def RDT_send_file(source_address, target_address, file_path='./original.txt'):
    """
        You need to send the contents of the file in the specified file path to target_address, depending on your design.
        In order to reduce the impact of hardware, you can first read the contents of the file into memory before sending.

        Please note that this experiment should be finished locally. So you could
        set the ProxyServerAddress of your RDTSocket as your true destination, rather
        than the adress of proxy_server.
        params:
            target_address:    Target IP address and its port
            source_address:    Source IP address and its port
            file_path:         The file you need to send
    """
    client = RDTSocket()
    client.bind(target_address)
    client.listen(5)
    client.connect(source_address)
    file_path = './original.txt'
    with open(file_path, "rb") as file:
        data = file.read()
        client.send(source_address, data)
        print(f"Client connected to {source_address}")
    client.close()
    return


def RDT_receive_file(source_address, target_address, file_path='./transmit_rdt.txt'):
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
    server = RDTSocket()
    server.bind(source_address)
    server.listen(5)
    while True:
        try:
            addr = server.accept()
            if addr == target_address:
                start_time = time.time()
                data_received = server.recv(address=addr)
                print(f"time_used: {time.time() - start_time} s")
                break
        except KeyboardInterrupt:
            break
        except:
            continue

    print(f"Server connected to {addr}")
    print(data_received)
    with open(file_path, "wb") as file:
        for i in data_received:
            file.write(i)
    server.close()
    return


def test_file_integrity(original_path, transmit_path):
    with open(original_path, 'rb') as file1, open(transmit_path, 'rb') as file2:
        print("Conducting file integrity test.")
        while True:
            block1 = file1.read(4096)
            block2 = file2.read(4096)

            if block1 != block2:
                raise Exception("Contents is different")

            if not block1:
                break

    return True


def test_throughput():
    # UDP
    try:
        UDP_start_test()
    except Exception as e:
        print(e)

    # Yours
    try:
        RDT_start_test()
        test_file_integrity('./original.txt', './transmit_rdt.txt')
    except Exception as e:
        print(e)


if __name__ == '__main__':
    test_throughput()
