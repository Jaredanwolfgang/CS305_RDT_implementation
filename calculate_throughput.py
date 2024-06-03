import signal
import socket
import os
import threading
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


def RDT_start_test(port_source=12345):
    sender_1 = Process(target=RDT_send_file, args=(("127.0.0.1", port_source), ("127.0.0.1", 12346)))
    sender_2 = Process(target=RDT_send_file, args=(("127.0.0.1", port_source), ("127.0.0.1", 12347)))
    sender_3 = Process(target=RDT_send_file, args=(("127.0.0.1", port_source), ("127.0.0.1", 12348)))
    receiver = Process(target=RDT_receive_file, args=(("127.0.0.1", port_source),))

    receiver.start()
    time.sleep(2)
    sender_1.start()
    sender_2.start()
    sender_3.start()

    sender_1.join()
    sender_2.join()
    sender_3.join()
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


recv_queue = queue.Queue()

def Run(server):
    cnt = 0
    threads = []
    while True:
        addr = recv_queue.get()
        cnt += 1
        thread = server.recv(address=addr)
        threads.append(thread)
        print(f"Server connected to {addr}")
        if cnt == 3:
            break

    for t in threads:
        t.start()

    for t in threads:
        t.join()
    return


def RDT_receive_file(source_address):
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
    global recv_queue
    server = RDTSocket()
    server.bind(source_address)
    server.listen(5)
    t = threading.Thread(target=Run, args=(server,))
    t.start()
    cnt = 0
    while True:
        try:
            addr = server.accept()
            recv_queue.put(addr)
            cnt += 1
            if cnt == 3:
                break
        except KeyboardInterrupt:
            break
        except:
            continue
    t.join()
    answer = server.answer_dict
    print(answer.keys())
    cnt = 1
    for key in answer:
        file_path = 'transmit_rdt' + str(cnt) + '.txt'
        with open(file_path, "wb") as file:
            for i in answer[key]:
                file.write(i)
        cnt += 1
    server.close()
    return

def test_file_integrity(original_path, transmit_path):
    with open(original_path, 'rb') as file1, open('./transmit_rdt1.txt', 'rb') as file2, open('./transmit_rdt2.txt', 'rb') as file3, open('./transmit_rdt3.txt', 'rb') as file4:
        print("Conducting file integrity test.")
        while True:
            block1 = file1.read(4096)
            block2 = file2.read(4096)
            block3 = file3.read(4096)
            block4 = file4.read(4096)

            if block1 != block2:
                raise Exception("Contents 1 is different")
            if block1 != block3:
                raise Exception("Contents 2 is different")
            if block1 != block4:
                raise Exception("Contents 3 is different")
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
        test_file_integrity('./original.txt', './transmit_rdt0.txt')
    except Exception as e:
        print(e)


if __name__ == '__main__':
    test_throughput()
