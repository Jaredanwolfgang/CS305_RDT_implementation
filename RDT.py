import socket
import random
import threading
import time
from Header import RDTHeader
from concurrent.futures import ThreadPoolExecutor

# References:
# https://realpython.com/python-sockets/
# https://github.com/ethay012/TCP-over-UDP/blob/master/TCP_over_UDP.py

DATA_DIVIDE_LENGTH = 256
RDT_HEADER_LENGTH = 42
DATA_LENGTH = DATA_DIVIDE_LENGTH
SENT_SIZE = RDT_HEADER_LENGTH + DATA_LENGTH
SEQ_LEFT = 0
SEQ_RIGHT = 1000

class RDTSocket():
    sender_state = ['Wait for call 0 from above', 'Wait for call 1 from above', 'Wait for ACK 0', 'Wait for ACK 1']
    
    def __init__(self) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.status = 1 # Socket open or close
        self.socket = None # Global Socket
        self.address = None
        self.port = None
    
        self.conn_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        
        # Received Packets as Sever
        self.packets = {"SYN": {}, "ACK": {}, "SYN_ACK": {}, "FIN_ACK": {}, "DATA": {}}
        # Established Connection as Client
        self.conn = {} # Established Connection
        # Pending Connection
        self.conn_queue = []
    
    def bind(self, address: (str, int)): # type: ignore
        """
        When trying to establish a connection. The socket must be bound to an address 
        and listening for connections. address is the address bound to the socket on 
        the other end of the connection.

        This function should be blocking. 
        
        params: 
            address:    Target IP address and its port
        """
        self.address = address[0]
        self.port = address[1]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.address, self.port))
        
    def listen_handler(self):
        while True and self.status:
            try:
                data, address = self.socket.recvfrom(SENT_SIZE)
                packet = RDTHeader()
                packet.from_bytes(data)
                
                # Sort the incoming data based upon type and sources
                if packet.SYN == 1 and packet.ACK == 0:
                    self.packets["SYN"][address] = packet
                    print(f"Receiving SYN data {packet} from {address}")
                elif packet.SYN == 1 and packet.ACK == 1:
                    self.packets["SYN_ACK"][address] = packet
                    print(f"Receiving SYN_ACK data {packet} from {address}")
                elif packet.FIN == 1 and packet.ACK == 1:
                    self.packets["FIN_ACK"][address] = packet
                    print(f"Receiving FIN_ACK data {packet} from {address}")
                elif packet.ACK == 1 and packet.FIN == 0 and packet.SYN == 0 and (packet.PAYLOAD is None or packet.PAYLOAD == ""):
                    self.packets["ACK"][address] = packet
                    print(f"Receiving ACK data {packet} from {address}")
                elif packet.PAYLOAD:
                    self.packets["DATA"][address] = packet
                    print(f"Receiving DATA {packet} from {address}")
                else:
                    print(f"Received {packet}")
                    
            except Exception as error:
                print(f"[Server] Problem in sorting incoming data: {error}")
                self.status = 0
                self.socket.close()

    def conn_handler(self, max_connections):
        while True and self.status:
            try:
                if self.packets["SYN"]:
                    address, packet = self.packets["SYN"].popitem()
                    if address not in self.conn.keys():
                        with self.queue_lock:
                            if len(self.conn_queue) < max_connections:
                                self.conn_queue.append((packet, address))
                                print(f"Adding connection from {address} to connection queue.")
                    else:
                        print(f"Connection with {address} already established.")
            except Exception as error:
                print(f"[Server] Problem when adding SYN request to connection queue: {error}")
                self.status = 0
                self.socket.close()
        
    def listen(self, max_connections=1):
        try:
            print("[Server] Start Listening.")
            sort_thread = threading.Thread(target=self.listen_handler, args=())
            conn_thread = threading.Thread(target=self.conn_handler, args=(max_connections, ))
            sort_thread.daemon = True
            sort_thread.start()
            conn_thread.start()
        except Exception as error:
            print(f"[Server] RDT Connection Establishment Error: {error}")
            self.socket.close()

    def accept(self): 
        """
        When using this SOCKET to create an RDT SERVER, it should accept the connection
        from a CLIENT. After that, an RDT connection should be established.
        Please note that this function needs to support multithreading and be able to 
        establish multiple socket connections. Messages from different sockets should 
        be isolated from each other, requiring you to multiplex the data received at 
        the underlying UDP.
        """
        def send_SYN_ACK(address, SEQ_num, ACK_num):
            message_SYN_ACK = RDTHeader(1, 0, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_SYN_ACK.set_source_address(self.address, self.port)
            message_SYN_ACK.set_target_address(address[0], address[1])
            message_SYN_ACK.checksum_cal()
            return message_SYN_ACK
        
        def send_FIN_ACK(address, SEQ_num, ACK_num):
            message_FIN_ACK = RDTHeader(0, 1, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_FIN_ACK.set_source_address(self.address, self.port)
            message_FIN_ACK.set_target_address(address[0], address[1])
            message_FIN_ACK.checksum_cal()
            return message_FIN_ACK
        
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        try:
            while True:
                if self.conn_queue: # The connection queue stores relevant SYN data.
                    with self.queue_lock:
                       packet, address = self.conn_queue.pop()
                    
                    # Send SYN_ACK package
                    message_SYN_ACK = send_SYN_ACK(address, packet.ACK_num, packet.SEQ_num + 1)
                    self.socket.sendto(message_SYN_ACK.to_bytes(), address)
                    print(f"[Server] SYN_ACK packet sent.\n {message_SYN_ACK}")
                    
                    ack_answer = None
                    while ack_answer is None:
                        time.sleep(0.25)
                        try:
                            if address in self.packets["ACK"].keys():
                                ack_answer = self.packets["ACK"][address]
                        except socket.timeout:
                            self.socket.sendto(message_SYN_ACK.to_bytes(), address)
                    print(f"[Server] Received ACK answer.\n {ack_answer}")
                    
                    # Receive ACK response
                    self.conn[address] = ack_answer
                    print(f"[Server] Connection with {address} is created! There are currently {len(self.conn)} connections.")
                    return address
        except Exception as error:
            print(f"[Server] Accept() function finds error: {error.with_traceback}")
            self.status = 0
            self.socket.close()    
    
    def connect(self, address: (str, int)): # type: ignore
        """
        When using this SOCKET to create an RDT client, it should send the connection
        request to target SERVER. After that, an RDT connection should be established.
        
        params:
            address:    Target IP address and its port
        """
        def send_SYN(address, SEQ_num, ACK_num):
            message_SYN = RDTHeader(1, 0, 0, SEQ_num, ACK_num, 0, 0, None, 0)
            message_SYN.set_source_address(self.address, self.port)
            message_SYN.set_target_address(address[0], address[1])
            message_SYN.checksum_cal()
            return message_SYN
        
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        print("[Connect] Start Connection Establishment.")
        try:
            # Send SYN
            message_SYN = send_SYN(address, random.randint(SEQ_LEFT, SEQ_RIGHT), 0)
            self.socket.sendto(message_SYN.to_bytes(), address)
            print(f"[Client] Message SYN sent.\n {message_SYN}")
        
            # Receive SYN_ACK
            syn_ack_answer = None
            while syn_ack_answer is None:
                time.sleep(0.25)
                try:
                    if address in self.packets["SYN_ACK"].keys():
                        syn_ack_answer = self.packets["SYN_ACK"][address]
                except socket.timeout:
                    self.socket.sendto(message_SYN.to_bytes(), address)
            print(f"[Client] Message SYN_ACK received.\n {syn_ack_answer}")
            
            # Send ACK
            message_ACK = send_ACK(address, syn_ack_answer.ACK_num, syn_ack_answer.SEQ_num + 1)
            self.socket.sendto(message_ACK.to_bytes(), address)
            print(f"[Client] Message ACK sent.\n {message_ACK}")
            
            # Connection established
            self.conn[address] = syn_ack_answer
            print(f"[Client] Connection with {address} is created!")
            
        except Exception as error:
            print(f"[Client] RDT Connection Establishment Error: {error.with_traceback()}")
            self.socket.close()
            
    def rdt_send(self, address, data, SEQ_num, ACK_num):
        pass
        
    def send(self, data=None, tcpheader=None):
        """
        RDT can use this function to send specified data to a target that has already 
        established a reliable connection. Please note that the corresponding CHECKSUM 
        for the specified data should be calculated before computation. Additionally, 
        this function should implement flow control during the sending phase. Moreover, 
        when the data to be sent is too large, this function should be able to divide 
        the data into multiple chunks and send them to the destination in a pipelined 
        manner.
        
        params:
            data:       The data that will be sent.
            tcpheader:  Message header.Include SYN, ACK, FIN, CHECKSUM, etc. Use this
                        attribute when needed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        raise NotImplementedError()
    
    def recv(self):
        """
        You should implement the basic logic for receiving data in this function, and 
        verify the data. When corrupted or missing data packets are detected, a request 
        for retransmission should be sent to the other party.
        
        This function should be bolcking.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        raise NotImplementedError()
    
    
    def close(self):
        """
        Close current RDT connection.
        You should follow the 4-way-handshake, and then the RDT connection will be terminated.
        """
        def send_FIN_ACK(address, SEQ_num, ACK_num):
            message_FIN_ACK = RDTHeader(0, 1, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_FIN_ACK.set_source_address(self.address, self.port)
            message_FIN_ACK.set_target_address(address[0], address[1])
            message_FIN_ACK.checksum_cal()
            return message_FIN_ACK
        
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        try:
            for address, packet in self.conn.items():
                # Send FIN ACK
                message_FIN_ACK = send_FIN_ACK(address, packet.ACK_num, packet.SEQ_num + 1)
                self.socket.sendto(message_FIN_ACK.to_bytes(), address)
                
                # Receive ACK
                ack_answer = None
                while ack_answer is None:
                    time.sleep(0.25)
                    try:
                        if address in self.packets["ACK"].keys():
                            ack_answer = self.packets["ACK"][address]
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACK.to_bytes(), address)
                print(f"[Server] Received ACK answer.\n {ack_answer}")
                    
                # Receive FIN ACK
                fin_ack_answer = None
                while fin_ack_answer is None:
                    time.sleep(0.25)
                    try:
                        if address in self.packets["FIN_ACK"].keys():
                            fin_ack_answer = self.packets["FIN_ACK"][address]
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACKto_bytes(), address)
                print(f"[Server] Received FIN_ACK answer.\n {fin_ack_answer}")
                
                # Send ACK
                message_ACK = send_ACK(address, packet.ACK_num, packet.SEQ_num + 1)
                self.socket.sendto(message_ACK.to_bytes(), address)
                
                # Close Connection
                self.conn.pop(address)
        except Exception as error:
            print(f"[Client] RDT Connection Establishment Error: {error}")
            self.socket.close()