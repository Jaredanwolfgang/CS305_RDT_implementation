import socket
import threading
import time
from Header import RDTHeader
from collections import deque
class RcvObject:
    def __init__(self):
        self.condition = threading.Condition()
        self.is_ready = False
        self.data: bytes = b''
    def set_ready(self, data):
        with self.condition:
            self.is_ready = True
            self.condition.notify_all()
            self.data = data
    # def wait_for_ready(self):
    #     with self.condition:
    #         while not self.is_ready:
    #             self.condition.wait()
    #             # if timeout then send message
DATA_DIVIDE_LENGTH = 256
RDT_HEADER_LENGTH = 42
DATA_LENGTH = DATA_DIVIDE_LENGTH
SENT_SIZE = RDT_HEADER_LENGTH + DATA_LENGTH
SEQ_LEFT = 0
SEQ_RIGHT = 1000
class RDTSocket():

    def __init__(self) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.status = 1  # Socket open or close
        self.socket = None  # Global Socket
        self.address = None
        self.port = None
        self.timeout1 = 0.5
        self.timeout2 = 4
        self.global_lock = threading.Lock()
        self.send_lock = threading.Lock()
        self.map_rcv_lock = threading.Lock()
        self.map_rcv = {}

    def bind(self, address: (str, int)): # type: ignore
        """
        When trying to establish a connection. The socket must be bound to an address 
        and listening for connections. address is the address bound to the socket on 
        the other end of the connection.

     
        
        params: 
            address:    Target IP address and its port
        """
        self.address = address[0]
        self.port = address[1]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.address, self.port))
    # send_lock
    def udt_send(self, address, data, SEQ_num, ACK_num):
        sndpkt = RDTHeader(0, 0, 0, SEQ_num, ACK_num, len(data), 0, data, 0)
        sndpkt.set_source_address(self.address, self.port)
        sndpkt.set_target_address(address[0], address[1])
        sndpkt.checksum_cal()
        return sndpkt
    def tunnel_send(self, message, address):
        self.send_lock.acquire()
        self.socket.sendto(message, address)
        self.send_lock.release()

    def corrupt(self, rcvpkt):
        rcv_checksum = rcvpkt.CHECKSUM
        rcvpkt.checksum_cal()
        if rcv_checksum == rcvpkt.CHECKSUM:
            return False
        else:
            return True
    def msg_server(self, address, pkt, state, SEQ_num, ACK_num, Fin):

        if pkt.SYN == 1 and pkt.ACK == 0:
            message_SYN_ACK = RDTHeader(1, 0, 1, pkt.ACK_num, pkt.SEQ_num + 1, 0, 0, None, 0)
            message_SYN_ACK.set_source_address(self.address, self.port)
            message_SYN_ACK.set_target_address(address[0], address[1])
            message_SYN_ACK.checksum_cal()
            return message_SYN_ACK.to_bytes(), state, SEQ_num, ACK_num, Fin
        elif pkt.FIN == 1 and pkt.ACK == 1:
            Fin = 1
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, 0)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK.to_bytes(), state, SEQ_num, ACK_num, Fin
        elif Fin == 1 and pkt.ACK == 1 and pkt.PAYLOAD == "":
            Fin = 2
            return None, -1, 0, 0, Fin
        else:
            res = None
            if state == 0:
                print("[Receiver] Wait for 0 from below")
                if self.corrupt(pkt) or pkt.SEQ_num != 0:
                    res = pkt.to_bytes()
                elif pkt.SEQ_num == 0:
                    print("Received non-corrupted packet.")
                    SEQ_num, ACK_num, state = pkt.ACK_num, 0, 1
                    data = pkt.PAYLOAD
                    res = self.udt_send(address, data, SEQ_num, ACK_num)
            elif state == 1:
                print("[Receiver] Wait for 1 from below")
                if (self.corrupt(pkt) or pkt.SEQ_num != 1):
                    res = pkt.to_bytes()
                elif pkt.SEQ_num == 0:
                    print("Received non-corrupted packet.")
                    SEQ_num, ACK_num, state = pkt.ACK_num, 1, 0
                    data = pkt.PAYLAOD.encode() if isinstance(pkt.PAYLOAD, str) else "".encode()
                    res = self.udt_send(address, data, SEQ_num, ACK_num)
            return res, state, SEQ_num, ACK_num, Fin

    def Run(self, address):
        self.map_rcv_lock.acquire()
        rcv = self.map_rcv[address]
        self.map_rcv_lock.release()
        state, SEQ_num, ACK_num, Fin = -1, 0, 0, 0
        while Fin != 2:
            send_msg, state, SEQ_num, ACK_num, Fin = self.msg_server(address, RDTHeader().from_bytes(rcv.data), state, Fin)
            if send_msg is None:
                continue
            with rcv.condition:
                timer1 = time.time()
                timer2 = 0
                while not rcv.is_ready:
                    rcv.condition.wait()
                    if time.time() - timer1 > self.timeout1:
                        self.tunnel_send(send_msg, address)
                        timer1 = time.time()
                        timer2 += 1
                    if timer2 > self.timeout2:
                        self.map_rcv_lock.acquire()
                        del self.map_rcv[address]
                        self.map_rcv_lock.release()
                        return


    def accept(self): # type: ignore
        """
        When using this SOCKET to create an RDT SERVER, it should accept the connection
        from a CLIENT. After that, an RDT connection should be established.
        Please note that this function needs to support multithreading and be able to 
        establish multiple socket connections. Messages from different sockets should 
        be isolated from each other, requiring you to multiplex the data received at 
        the underlying UDP.

        This function should be blocking. 

        """
        while True:
            try:
                data, address = self.socket.recvfrom(256)
                self.map_rcv_lock.acquire()
                if address not in self.map_rcv:
                    self.map_rcv[address] = RcvObject()
                    t = threading.Thread(target=self.Run, args=(address,))
                    t.start()
                self.map_rcv[address].set_ready(data)
                self.map_rcv_lock.release()
            except socket.timeout:
                print("Timeout occurred")
                # retry
    
    def connect(self, address: (str, int)): # type: ignore
        """
        When using this SOCKET to create an RDT client, it should send the connection
        request to target SERVER. After that, an RDT connection should be established.
        
        params:
            address:    Target IP address and its port
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        raise NotImplementedError()
    
    def send(self, data=None, tcpheader=None, test_case=0):
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
            test_case:  Indicate the test case will be used in this experiment
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
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        raise NotImplementedError()