import socket
import random
import threading
import time
from Header import RDTHeader
import congestion
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

    def __init__(self) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.status = 1 # Socket open or close
        self.socket = None # Global Socket
        self.address = None
        self.port = None
        self.timeout = 5
    
        # Received Packets as Sever
        self.packets = {"SYN": {}, "ACK": {}, "SYN_ACK": {}, "FIN_ACK": {}, "DATA": {}}
        # Established Connection as Client
        self.conn = {} # Established Connection
        # Pending Connection
        self.conn_queue = []
        self.conn_lock = None
        self.queue_lock = None
        self.packets_lock = None

        # Threads
        self.sort_thread = None
        self.conn_thread = None

        self.maxsize = 512

        # Proxy Configuration, if tested locally, the proxy is the same as the target address
        self.isLocalTest = False
        self.fromSenderAddr = ('10.16.52.94', 12345)  # FromSender
        self.fromReceiverAddr = ('10.16.52.94', 12347)  # FromReceiver

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
        self.socket.settimeout(32)

    def TransAddr(self, addr):
        return (str(addr[0]) + '.' + str(addr[1]) + '.' + str(addr[2]) + '.' + str(addr[3]), addr[4])

    def listen_handler(self):
        while True and self.status:
            try:
                data = None
                address = None
                while data is None:
                    data, _ = self.socket.recvfrom(SENT_SIZE)
                    self.maxsize += 1
                    # print(f"{self.port}: Received!")
                    packet = RDTHeader()
                    packet.from_bytes(data)
                    address = self.TransAddr(packet.Source_address)
                with self.packets_lock:
                    # Sort the incoming data based upon type and sources
                    if packet.SYN == 1 and packet.ACK == 0:
                        self.packets["SYN"][address] = packet
                        # print(f"[{(self.address, self.port)}] Receiving SYN data {packet} from {address}")
                    elif packet.SYN == 1 and packet.ACK == 1:
                        self.packets["SYN_ACK"][address] = packet
                        # print(f"[{(self.address, self.port)}] Receiving SYN_ACK data {packet} from {address}")
                    elif packet.FIN == 1 and packet.ACK == 1:
                        self.packets["FIN_ACK"][address] = packet
                        # print(f"[{(self.address, self.port)}] Receiving FIN_ACK data {packet} from {address}")
                    elif packet.ACK == 1 and packet.FIN == 0 and packet.SYN == 0 and (packet.PAYLOAD is None or packet.PAYLOAD == ""):
                        self.packets["ACK"][address] = packet
                        # print(f"[{(self.address, self.port)}] Receiving ACK data {packet} from {address}")
                    elif packet.PAYLOAD:
                        # print (f"get {packet} end... \n")
                        if(self.packets["DATA"].get(address) is None):
                            # print(f"packets in {address}")
                            self.packets["DATA"][address] = [packet]
                        else:
                            self.packets["DATA"][address].append(packet)
                        # print(f"[{(self.address, self.port)}] Receiving DATA {packet} from {address}")
                    else:
                        # print(f"[{(self.address, self.port)}] Received {packet}")
                        pass
            except Exception as error:
                print(f"[Server] Problem in sorting incoming data: {error}")
                self.status = 0
                self.socket.close()

    def conn_handler(self, max_connections):
        while True and self.status:
            try:
                with self.packets_lock:
                    if self.packets["SYN"]:
                        address, packet = self.packets["SYN"].popitem()
                        if address not in self.conn.keys():
                            with self.queue_lock:
                                if len(self.conn_queue) < max_connections:
                                    self.conn_queue.append((packet, address))
                                    # print(f"Adding connection from {address} to connection queue.")
                        else:
                            print(f"Connection with {address} already established.")
            except Exception as error:
                print(f"[Server] Problem when adding SYN request to connection queue: {error}")
                self.status = 0
                self.socket.close()
        
    def listen(self, max_connections=1):
        self.conn_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        self.packets_lock = threading.Lock()
        try:
            print("[Server] Start Listening.")
            self.sort_thread = threading.Thread(target=self.listen_handler, daemon=True, args=())
            self.conn_thread = threading.Thread(target=self.conn_handler, daemon=True, args=(max_connections, ))
            self.sort_thread.daemon = True
            self.sort_thread.start()
            self.conn_thread.start()
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
            message_SYN_ACK = RDTHeader(1, 0, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_SYN_ACK.set_source_address(self.address, self.port)
            message_SYN_ACK.set_target_address(address[0], address[1])
            message_SYN_ACK.checksum_cal()
            return message_SYN_ACK
        
        try:
            while True:
                if self.conn_queue: # The connection queue stores relevant SYN data.
                    with self.queue_lock:
                       packet, address = self.conn_queue.pop()
                    
                    # Send SYN_ACK package
                    message_SYN_ACK = send_SYN_ACK(address, packet.ACK_num, packet.SEQ_num + 1)

                    self.socket.sendto(message_SYN_ACK.to_bytes(), address if self.isLocalTest else self.fromReceiverAddr)
                    # print(f"[Server] SYN_ACK packet sent.\n {message_SYN_ACK}")
                    
                    ack_answer = None
                    while ack_answer is None:
                        try:
                            if address in self.packets["ACK"].keys():
                                ack_answer = self.packets["ACK"].pop(address)
                                self.maxsize += 1
                        except self.socket.timeout:
                            self.socket.sendto(message_SYN_ACK.to_bytes(), address if self.isLocalTest else self.fromReceiverAddr)
                    # print(f"[Server] Received ACK answer.\n {ack_answer}")
                    
                    # Receive ACK response
                    with self.conn_lock:
                        self.conn[address] = "Wait for 0 from below"
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
            message_SYN = RDTHeader(1, 0, 0, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_SYN.set_source_address(self.address, self.port)
            message_SYN.set_target_address(address[0], address[1])
            message_SYN.checksum_cal()
            return message_SYN
        
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        print("[Connect] Start Connection Establishment.")
        try:
            # Send SYN
            message_SYN = send_SYN(address, random.randint(SEQ_LEFT, SEQ_RIGHT), 0)
            self.socket.sendto(message_SYN.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
            # print(f"[Client] Message SYN sent.\n {message_SYN}")
        
            # Receive SYN_ACK
            syn_ack_answer = None
            while syn_ack_answer is None:
                try:
                    if address in self.packets["SYN_ACK"].keys():
                        syn_ack_answer = self.packets["SYN_ACK"].pop(address)
                        self.maxsize += 1
                except self.socket.timeout:
                    self.socket.sendto(message_SYN.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
            # print(f"[Client] Message SYN_ACK received.\n {syn_ack_answer}")
            
            # Send ACK
            message_ACK = send_ACK(address, syn_ack_answer.ACK_num, syn_ack_answer.SEQ_num + 1)
            self.socket.sendto(message_ACK.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
            # print(f"[Client] Message ACK sent.\n {message_ACK}")
            
            # Connection established
            with self.conn_lock:
                self.conn[address] = "Wait for call 0 from above"
            print(f"[Client] Connection with {address} is created!")
            
        except Exception as error:
            print(f"[Client] RDT Connection Establishment Error: {error.with_traceback()}")
            self.socket.close()
            
    # def udt_send(self, address, data, SEQ_num, ACK_num):
    #     sndpkt = RDTHeader(0, 0, 0, SEQ_num, ACK_num, len(data), 0, data, 0)
    #     sndpkt.set_source_address(self.address, self.port)
    #     sndpkt.set_target_address(address[0], address[1])
    #     sndpkt.checksum_cal()
    #     self.socket.sendto(sndpkt.to_bytes(), address)
    #     # print(f"[{(self.address, self.port)}] Message sent.\n {sndpkt} \n End Packet.\n")
    #     return time.time() # Start Timer

    def udt_send_t(self, address, data, SEQ_num, ACK_num, proxy, test_case=20) -> None:
        sndpkt = RDTHeader(0, 0, 0, SEQ_num, ACK_num, len(data), 0, data, self.maxsize)
        sndpkt.set_test_case(test_case)
        sndpkt.set_source_address(self.address, self.port)
        sndpkt.set_target_address(address[0], address[1])
        sndpkt.checksum_cal()
        try:
            self.socket.sendto(sndpkt.to_bytes(), proxy)
        except OSError as e:
            pass


    def corrupt(self, rcvpkt):
        rcv_checksum = rcvpkt.CHECKSUM
        # print(f"Received packet checksum: {rcvpkt.CHECKSUM}")
        rcvpkt.checksum_cal()
        # print(f"Calculated packet checksum: {rcvpkt.CHECKSUM}")
        if rcv_checksum == rcvpkt.CHECKSUM:
            return False
        else:
            return True
        
    def send(self, address, data=None, tcpheader=None, test_case=20):
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
        # The received data is allocated to the packets dictionary, we only need to process the data in the queue of
        # the corresponding address. Here should be a finite state machine for deciding the states of sending the data.
        data_seg = [data[i:i+DATA_DIVIDE_LENGTH] for i in range(0, len(data), DATA_DIVIDE_LENGTH)] # Data segmentation
        timer = None
        SEQ_num = 0 # Byte Stream "number" of the first byte in the data
        ACK_num = 0 # Byte Stream "number" of the next byte expected by the sender

        def ByteId(x) -> int:
            return x // DATA_DIVIDE_LENGTH
        is_acked = [False for _ in range(len(data_seg))]
        un_acked = [i for i in range(len(data_seg))]
        ctrl = congestion.CongestionController()
        rwnd = 512
        state_cnt, cwnd_last = 0, -1
        while len(un_acked) != 0:
            cwnd, cnt = min(ctrl.cwnd, rwnd), 0
            st = []
            print(cwnd, len(un_acked))
            state_cnt = state_cnt + 1 if cwnd_last == cwnd else 0
            maxt = 0.3 if state_cnt >= 8 else 2
            cwnd_last = cwnd
            with self.packets_lock:
                self.packets["DATA"][address] = []

            RTT = time.time()
            while cwnd != 0 and len(un_acked) != 0:
                seq = un_acked.pop(0)
                st.append(seq)
                SEQ_num = seq * DATA_DIVIDE_LENGTH
                ACK_num = SEQ_num + len(data_seg[seq])
                self.udt_send_t(address, data_seg[seq], SEQ_num, ACK_num, address if self.isLocalTest else self.fromSenderAddr, test_case)
                cwnd -= 1
                cnt += 1
            probe_time = 31
            while True:
                probe_time += 1
                if probe_time != 32:
                    continue
                probe_time = 0
                with self.packets_lock:
                    if len(self.packets["DATA"][address]) != 0:
                        break
                if time.time() - RTT >= min(maxt, ctrl.timeoutInterval):
                    break
            RTT = time.time() - RTT
            # print(RTT)
            timer = time.time()
            ctrl.set_timeout_interval(RTT)
            while cnt > 0:
                with self.packets_lock:
                    if len(self.packets["DATA"][address]) != 0:
                        pkt = self.packets["DATA"][address].pop()
                        rwnd = pkt.RWND
                        self.maxsize += 1
                        if not self.corrupt(pkt) and pkt.ACK_num > 0:
                            cnt -= not is_acked[ByteId(pkt.ACK_num - 1)]
                            is_acked[ByteId(pkt.ACK_num - 1)] = True
                if time.time() - timer >= min(maxt, ctrl.timeoutInterval):
                    break

            print(ctrl.timeoutInterval)
            # with self.packets_lock:
            #     q = self.packets["DATA"][address]
            # for pkt in q:
            #     if not self.corrupt(pkt) and pkt.ACK_num > 0:
            #         is_acked[ByteId(pkt.ACK_num - 1)] = True
            st.reverse()
            flag = True
            for i in st:
                if not is_acked[i]:
                    un_acked.insert(0, i)
                    flag = False
            if flag:
                ctrl.update()
            else:
                ctrl.timeout()

        self.close_conn_active(address, SEQ_num, ACK_num)
        return

    def recv(self, address, test_case=20):
        """
        You should implement the basic logic for receiving data in this function, and 
        verify the data. When corrupted or missing data packets are detected, a request 
        for retransmission should be sent to the other party.
        
        This function should be blocking.
        """
        timer = None
        SEQ_num = 0
        ACK_num = 0
        pkt_recv = {}
        while True:
            with self.conn_lock:
                if address not in self.conn.keys():
                    break
            with self.packets_lock:
                if address in self.packets["FIN_ACK"].keys():
                    break
                if address not in self.packets["DATA"].keys() or len(self.packets["DATA"][address]) == 0:
                    continue
                q = self.packets["DATA"][address].copy()
                self.maxsize += len(q)
                self.packets["DATA"][address] = []
            for pkt in q:
                if self.corrupt(pkt):
                    continue
                data: str = " "
                self.udt_send_t(address, data, pkt.ACK_num, pkt.ACK_num, address if self.isLocalTest else self.fromReceiverAddr, test_case=test_case)
                if pkt.ACK_num != pkt.SEQ_num:
                    pkt_recv[pkt.SEQ_num] = pkt.PAYLOAD.encode()
        self.close_conn_passive(address, SEQ_num, ACK_num)
        res = sorted(pkt_recv)
        return [pkt_recv[key] for key in res]
    
    def close_conn_active(self, address, SEQ_num, ACK_num):
        def send_FIN_ACK(address, SEQ_num, ACK_num):
            message_FIN_ACK = RDTHeader(0, 1, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_FIN_ACK.set_source_address(self.address, self.port)
            message_FIN_ACK.set_target_address(address[0], address[1])
            message_FIN_ACK.checksum_cal()
            return message_FIN_ACK
            
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        try:
            if address in self.conn.keys():
                # Send FIN ACK
                message_FIN_ACK = send_FIN_ACK(address, SEQ_num, ACK_num)
                self.socket.sendto(message_FIN_ACK.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
                # print(f"[Sender] Message FIN_ACK sent.\n {message_FIN_ACK}")
                
                # Receive ACK
                ack_answer = None
                while ack_answer is None:
                    # time.sleep(0.25)
                    try:
                        with self.packets_lock:
                            if address in self.packets["ACK"].keys():
                                ack_answer = self.packets["ACK"].pop(address)
                                self.maxsize += 1
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACK.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
                # print(f"[Sender] Received ACK answer.\n {ack_answer}")
                
                # Receive FIN ACK
                fin_ack_answer = None
                while fin_ack_answer is None:
                    # time.sleep(0.25)
                    try:
                        with self.packets_lock:   
                            if address in self.packets["FIN_ACK"].keys():
                                fin_ack_answer = self.packets["FIN_ACK"].pop(address)
                                self.maxsize += 1
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACK.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
                # print(f"[Sender] Received FIN_ACK answer.\n {fin_ack_answer}")
                
                # Send ACK
                message_ACK = send_ACK(address, fin_ack_answer.ACK_num, fin_ack_answer.SEQ_num + 1)
                self.socket.sendto(message_ACK.to_bytes(), address if self.isLocalTest else self.fromSenderAddr)
                # print(f"[Sender] Send ACK message.\n {message_ACK}")
                
                # Close connection
                with self.conn_lock:
                    self.conn.pop(address)
                # print(f"[Sender] Connection to {address} closed. Current active connections are: {self.conn.keys()}")
                return
        except Exception as error:
            print(f"[Sender] RDT 4-way handshake close {address} connection failed with {error}")
            self.socket.close()
            
    def close_conn_passive(self, address, SEQ_num, ACK_num):
        def send_FIN_ACK(address, SEQ_num, ACK_num):
            message_FIN_ACK = RDTHeader(0, 1, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_FIN_ACK.set_source_address(self.address, self.port)
            message_FIN_ACK.set_target_address(address[0], address[1])
            message_FIN_ACK.checksum_cal()
            return message_FIN_ACK
            
        def send_ACK(address, SEQ_num, ACK_num):
            message_ACK = RDTHeader(0, 0, 1, SEQ_num, ACK_num, 0, 0, None, self.maxsize)
            message_ACK.set_source_address(self.address, self.port)
            message_ACK.set_target_address(address[0], address[1])
            message_ACK.checksum_cal()
            return message_ACK
        
        try: 
            with self.packets_lock:
                if address in self.packets["FIN_ACK"].keys():
                    fin_ack_answer = self.packets["FIN_ACK"].pop(address)
            # print(f"[Receiver] Received FIN_ACK answer.\n {fin_ack_answer}")
                
            # Send ACK
            message_ACK = send_ACK(address, fin_ack_answer.ACK_num, fin_ack_answer.SEQ_num + 1)
            self.socket.sendto(message_ACK.to_bytes(), address if self.isLocalTest else self.fromReceiverAddr)
            # self.socket.sendto(message_ACK.to_bytes(), address)
            # print(f"[Receiver] Message ACK sent.\n {message_ACK}")
                
            # Send FIN ACK
            message_FIN_ACK = send_FIN_ACK(address, SEQ_num, ACK_num)
            self.socket.sendto(message_FIN_ACK.to_bytes(), address if self.isLocalTest else self.fromReceiverAddr)
            # print(f"[Receiver] Message FIN_ACK sent.\n {message_FIN_ACK}")
            
            # Receive ACK
            ack_answer = None
            while ack_answer is None:
                # time.sleep(0.25)
                try:
                    with self.packets_lock:
                        if address in self.packets["ACK"].keys():
                            ack_answer = self.packets["ACK"].pop(address)
                            self.maxsize += 1
                except socket.timeout:
                    self.socket.sendto(message_FIN_ACK.to_bytes(), address if self.isLocalTest else self.fromReceiverAddr)
            # print(f"[Receiver] Received ACK answer.\n {ack_answer}")

            # Close connection
            with self.conn_lock:
                self.conn.pop(address)
            # print(f"[Receiver] Connection from {address} closed. Current active connections are {self.conn.keys()}")
            return
        except Exception as error:
            print(f"[Receiver] RDT 4-way handshake close {address} connection failed with {error}")
            self.socket.close()      
    
    def close(self):
        """
        Close current RDT connection.
        You should follow the 4-way-handshake, and then the RDT connection will be terminated.
        """
        try:
            for address, state in self.conn.items():
                self.close_conn_active(address, 0, 1)
            if self.socket:
                self.socket.close()
            self.status = 0
        except Exception as error:
            print(f"[Client] RDT Connection Closd failed with: {error}")
            if self.socket:
                self.socket.close()