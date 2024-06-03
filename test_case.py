import socket
import time
from RDT import RDTSocket
from multiprocessing import Process
import signal

# connect proxy server 

proxy_server_address = ('10.16.52.94', 12234)   # ProxyServerAddress
fromSenderAddr = ('10.16.52.94', 12345)         # FromSender
toReceiverAddr = ('10.16.52.94', 12346)         # ToSender
fromReceiverAddr = ('10.16.52.94', 12347)       # FromReceiver
toSenderAddr = ('10.16.52.94', 12348)           # ToReceiver

resultAddr = ('10.16.52.94', 12230)

sender_address = ("10.28.4.180", 12344)         # Your sender address
receiver_address = ("10.28.4.180", 12349)       # Your receiver address



# connect locally server

#proxy_server_address = ('127.0.0.1', 12234)
#fromSenderAddr = ('127.0.0.1', 12345)
#toReceiverAddr = ('127.0.0.1', 12346)
#fromReceiverAddr = ('127.0.0.1', 12347)
#toSenderAddr = ('127.0.0.1', 12348)

#sender_address = ("127.0.0.1", 12244)
#receiver_address = ("127.0.0.1", 12249)
#resultAddr = ("127.0.0.1", 12230)
num_test_case = 1

class TimeoutException(Exception):
    pass

def handler(signum, frame):
    raise TimeoutException


# signal.signal(signal.SIGALRM, handler)

def test_case():
    sender_sock = None
    receiver_sock = None

    for i in range(num_test_case):
        if sender_sock:
            del sender_sock
        if receiver_sock:
            del receiver_sock
        sender_sock = RDTSocket()   # You can change the initialize RDTSocket()
        receiver_sock = RDTSocket() # You can change the initialize RDTSocket()
        print(f"Start test case : {i}")

        try:
            result = RDT_start_test(sender_sock, receiver_sock, sender_address, receiver_address, i)
        except Exception as e:
            print(e)
        finally:

            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(resultAddr)
           
            client_sock.sendall(f"{sender_address}-{receiver_address}:{i}".encode())

            response = client_sock.recv(1024)

            client_sock.close()

            print(f"proxy result for test case {i} {response.decode()}")
            
            if response.decode() == 'True' and result:
                print(f"test case {i} pass")
            else:
                print(f"test case {i} fail")

            sender_sock.close()
            receiver_sock.close()

            #############################################################################
            time.sleep(5)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(f"{sender_address}-{receiver_address}".encode(), proxy_server_address)
            time.sleep(10)
    

def RDT_start_test(sender_sock, receiver_sock, client_address, server_address, test_case):
    sender = Process(target=RDT_send, args=(sender_sock, server_address, client_address, test_case))
    receiver = Process(target=RDT_receive, args=(receiver_sock, server_address, test_case))

    receiver.start()
    time.sleep(5)
    sender.start()

    # if test_case < 5:
    #     signal.alarm(20)
    # else:
    #     signal.alarm(120)

    sender.join()
    receiver.join()
    time.sleep(1)

    # signal.alarm(0)

    if test_case < 5:
        return True
    else:
        return test_file_integrity('original.txt', 'transmit.txt')
    
def RDT_send(sender_sock: RDTSocket, source_address, target_address, test_case):
    """
        You should refer to your own implementation to implement this code. the sender should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params:
            source_address:    Server IP address and its port
            target_address:    Client IP address and its port
            test_case:         The rank of test case
    """
    client = sender_sock
    # client.proxy_server_addr = fromSenderAddr
    client.bind(target_address)
    client.connect(source_address)

    if test_case >= 5:
        file_path = './original.txt'
        with open(file_path, 'rb') as file:
            data = file.read()
            client.send(source_address, data=data, test_case=test_case)
        print(f"Large data file: Client connected to {source_address}")
    else:
        data = "Short Message test"
        client.send(source_address, data=data, test_case=test_case)
        print(f"Short Message: Client connected to {source_address}")


def RDT_receive(receiver_sock: RDTSocket, source_address, test_case):
    """
        You should refer to your own implementation to implement this code. the receiver should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params: 
            source_address:    Source IP address and its port
            test_case:         The rank of test case
    """
    server = receiver_sock
    # server.proxy_server_addr = fromReceiverAddr
    print(source_address)
    server.bind(source_address)
    addr = server.accept()
    file_path = './transmit_rdt.txt'
    if test_case >= 5:
        thread = server.recv(address=addr)
        thread.start()
        thread.join()
        answer = server.answer_dict[addr]
        print(f"Server connected to {addr}")
        with open(file_path, "wb") as file:
            for i in answer[addr]:
                file.write(i)
        print("Large file transmitted, please check out the transmit file.")
    else:
        thread = server.recv(address=addr)
        thread.start()
        thread.join()
        answer = server.answer_dict[addr]
        print(f"Server connected to {addr}")
        print(f"Smalle message: Received {answer}")


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