import socket
import string
import time
import random

from RDT import RDTSocket
from multiprocessing import Process
import signal

# connect proxy server 

proxy_server_address = ('10.16.52.94', 12234)   # ProxyServerAddress
fromSenderAddr = ('10.16.52.94', 12345)         # FromSender
# toReceiverAddr = ('10.16.52.94', 12346)         # ToSender
fromReceiverAddr = ('10.16.52.94', 12347)       # FromReceiver
# toSenderAddr = ('10.16.52.94', 12348)           # ToReceiver

resultAddr = ('10.16.52.94', 12230)

# TODO: Change to your own IP address here
LOCAL_IP = '10.32.72.227'
sender_address = (LOCAL_IP, 12345)         # Your sender address
receiver_address = (LOCAL_IP, 12346)       # Your receiver address



# connect locally server

# proxy_server_address = ('127.0.0.1', 12234)
# fromSenderAddr = ('127.0.0.1', 12345)
# toReceiverAddr = ('127.0.0.1', 12346)
# fromReceiverAddr = ('127.0.0.1', 12347)
# toSenderAddr = ('127.0.0.1', 12348)
#
# sender_address = ("127.0.0.1", 12244)
# receiver_address = ("127.0.0.1", 12249)
# resultAddr = ("127.0.0.1", 12230)
num_test_case = 16

class TimeoutException(Exception):
    pass

def handler(signum, frame):
    raise TimeoutException


# signal.signal(signal.SIGALRM, handler)

def test_case():
    # TODO: You could change the range of this loop to test specific case(s) in local test.
    sender_sock = None
    receiver_sock = None
    for i in range(8, num_test_case):
    # for i in :
        if sender_sock:
            del sender_sock
        if receiver_sock:
            del receiver_sock
        sender_sock = RDTSocket()    # You can change the initialize RDTSocket()
        receiver_sock = RDTSocket()  # You can change the initialize RDTSocket()
        print(f"\n\n[Case {i}] Start test.")

        try:
            result = RDT_start_test(sender_sock, receiver_sock, sender_address, receiver_address, i)
        except Exception as e:
            print(e)
        finally:

            print(f"\n[Case {i}] Finally")

            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(resultAddr)
           
            client_sock.sendall(f"{sender_address}-{receiver_address}:{i}".encode())

            response = client_sock.recv(1024)

            client_sock.close()

            print(f"proxy result for test case {i} {response.decode()}")
            print(f"test case {i}, validation = {result}")
            if response.decode() == 'True' and result:
                print(f"test case {i} pass")
            else:
                print(f"test case {i} fail")


            #############################################################################
            #TODO you should close your socket, and release the resource, this code just a 
            # demo. you should make some changes based on your code implementation or you can 
            # close them in the other places.

            print("[Test] Start to Close")

        #############################################################################
            time.sleep(5)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(f"{sender_address}-{receiver_address}".encode(), proxy_server_address) 


            time.sleep(10)
    

def RDT_start_test(sender_sock, receiver_sock, sender_address, receiver_address, test_case):
    print("RDT Test Start")
    sender = Process(target=RDT_send, args=(sender_sock, sender_address, receiver_address, test_case))
    receiver = Process(target=RDT_receive, args=(receiver_sock, receiver_address, test_case))
    receiver.start()
    time.sleep(5)
    sender.start()

    sender.join()
    receiver.join()
    time.sleep(1)

    return test_file_integrity('original.txt', 'transmit.txt')
    
def RDT_send(sender_sock: RDTSocket, sender_addr, receiver_addr, test_case):
    """
        You should refer to your own implementation to implement this code. the sender should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params: 
            target_address:    Target IP address and its port
            source_address:    Source IP address and its port
            test_case:         The rank of test case
    """

    # if test_case >= 5:
    #############################################################################
    # TODO: you need to send a files. Here you need to write the code according to your own implementation.

    sender_sock.bind(sender_addr)
    sender_sock.listen(5)
    print(f"[Sender] To Connect ...")
    sender_sock.connect(receiver_addr)

    with open("./original.txt", "w") as file:
        data = ''
        if test_case >= 5:
            sz = 3 * 1024  # 100KB
            data = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(sz))
        else:
            data = 'SUSTech'

        file.write(data)
    # time.sleep(1)
    with open('./original.txt', "rb") as file:
        data = file.read()
        print(f"[Sender] testcase {test_case} is sending {data}...")
        sender_sock.send(address=receiver_addr, data=data, test_case=test_case)

    sender_sock.close()

    #############################################################################
    # TODO: you need to send a short message. May be you can use
    # data = "Short Message test"
    # sock.send(data=data, test_case=test_case)
    #############################################################################



def RDT_receive(receiver_sock: RDTSocket, receiver_addr, test_case):
    """
        You should refer to your own implementation to implement this code. the receiver should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params: 
            source_address:    Source IP address and its port
            test_case:         The rank of test case
    """
    receiver_sock.bind(receiver_addr)
    receiver_sock.listen(5)
    data_received = b''
    addr = ''

    while True:
        try:
            addr = receiver_sock.accept()

            start_time = time.time()
            data_received = receiver_sock.recv(address=addr, test_case=test_case)
            print(f"time_used: {time.time() - start_time} s")
            break
        except KeyboardInterrupt:
            break

    print(f"Server connected to {addr}")
    print(data_received)
    with open('transmit.txt', "wb") as file:
        for i in data_received:
            file.write(i)
    print("[Receiver] end")

    receiver_sock.close()


def test_file_integrity(original_path, transmit_path):
    with open(original_path, 'rb') as file1, open(transmit_path, 'rb') as file2:
        while True:
            block1 = file1.read(4096)
            block2 = file2.read(4096)
            
            if block1 != block2:
                return False
            
            if not block1:
                break

    return True      


if __name__ == '__main__':
    test_case()