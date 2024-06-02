import socket
import random
import threading
import queue
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


class send_state(enumerate):
    WAIT_FOR_CALL_0 = 0
    WAIT_FOR_CALL_1 = 1
    WAIT_FOR_ACK_0 = 2
    WAIT_FOR_ACK_1 = 3


class receive_state(enumerate):
    WAIT_FOR_0_FROM_BELOW = 0
    WAIT_FOR_1_FROM_BELOW = 1


class RDTSocket():

    def __init__(self) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.status = 1  # Socket open or close
        self.socket = None  # Global Socket
        self.address = None
        self.port = None
        self.timeout = 1

        self.conn_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        self.packets_lock = threading.Lock()

        # Received Packets as Sever
        self.packets = {"SYN": {}, "ACK": {}, "SYN_ACK": {}, "FIN_ACK": {}, "DATA": {}}
        # Established Connection as Client
        self.conn = {}  # Established Connection
        # Pending Connection
        self.conn_queue = []

        # Threads
        self.sort_thread = None
        self.conn_thread = None

    def bind(self, address: (str, int)):  # type: ignore
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

    def listen_handler(self):
        print(f"[{(self.address, self.port)}] Listen handler is currently working.")
        while True and self.status:
            # timer = time.time()
            try:
                # data = None
                # address = None
                # while data is None:

                data, address = self.socket.recvfrom(SENT_SIZE)
                packet = RDTHeader()
                packet.from_bytes(data)
                # print(f"[{(self.address, self.port)}] Receive data after {time.time() - timer} seconds")

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
                    elif packet.ACK == 1 and packet.FIN == 0 and packet.SYN == 0 and (
                            packet.PAYLOAD is None or packet.PAYLOAD == ""):
                        self.packets["ACK"][address] = packet
                        # print(f"[{(self.address, self.port)}] Receiving ACK data {packet} from {address}")
                    elif packet.PAYLOAD:
                        # print (f"get {packet} end... \n")
                        if address in self.conn.keys():
                            self.conn[address].put(packet)
                            # print(f"[{(self.address, self.port)}] Receiving DATA {packet} from {address}")
                # print(f"Demultiplex data after {time.time() - timer} seconds")
            except Exception as error:
                print(f"[Server] Problem in sorting incoming data: {error}")
                self.status = 0
                self.socket.close()

    def conn_handler(self, max_connections):
        print(f"[{(self.address, self.port)}] Connection handler is currently working.")
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
            except Exception as error:
                print(f"[Server] Problem when adding SYN request to connection queue: {error}")
                self.status = 0
                self.socket.close()

    def listen(self, max_connections=1):
        try:
            # print("[Server] Start Listening.")
            self.sort_thread = threading.Thread(target=self.listen_handler, daemon=True, args=())
            self.conn_thread = threading.Thread(target=self.conn_handler, daemon=True, args=(max_connections,))
            self.sort_thread.start()
            self.conn_thread.start()
        except Exception as error:
            # print(f"[Server] RDT Connection Establishment Error: {error}")
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

        try:
            while True:
                if self.conn_queue:  # The connection queue stores relevant SYN data.
                    with self.queue_lock:
                        packet, address = self.conn_queue.pop()

                    # Send SYN_ACK package
                    message_SYN_ACK = send_SYN_ACK(address, packet.ACK_num, packet.SEQ_num + 1)
                    self.socket.sendto(message_SYN_ACK.to_bytes(), address)
                    # print(f"[Server] SYN_ACK packet sent.\n {message_SYN_ACK}")

                    ack_answer = None
                    while ack_answer is None:
                        try:
                            if address in self.packets["ACK"].keys():
                                ack_answer = self.packets["ACK"].pop(address)
                        except self.socket.timeout:
                            self.socket.sendto(message_SYN_ACK.to_bytes(), address)
                    # print(f"[Server] Received ACK answer.\n {ack_answer}")

                    # Receive ACK response
                    self.conn[address] = queue.Queue()
                    # print(f"[Server] Connection with {address} is created! There are currently {len(self.conn)} connections.")
                    return address
        except Exception as error:
            # print(f"[Server] Accept() function finds error: {error.with_traceback}")
            self.status = 0
            self.socket.close()

    def connect(self, address: (str, int)):  # type: ignore
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

        # print("[Connect] Start Connection Establishment.")
        try:
            # Send SYN
            message_SYN = send_SYN(address, random.randint(SEQ_LEFT, SEQ_RIGHT), 0)
            self.socket.sendto(message_SYN.to_bytes(), address)
            # print(f"[Client] Message SYN sent.\n {message_SYN}")

            # Receive SYN_ACK
            syn_ack_answer = None
            while syn_ack_answer is None:
                try:
                    if address in self.packets["SYN_ACK"].keys():
                        syn_ack_answer = self.packets["SYN_ACK"].pop(address)
                except self.socket.timeout:
                    self.socket.sendto(message_SYN.to_bytes(), address)
            # print(f"[Client] Message SYN_ACK received.\n {syn_ack_answer}")

            # Send ACK
            message_ACK = send_ACK(address, syn_ack_answer.ACK_num, syn_ack_answer.SEQ_num + 1)
            self.socket.sendto(message_ACK.to_bytes(), address)
            # print(f"[Client] Message ACK sent.\n {message_ACK}")

            # Connection established
            self.conn[address] = queue.Queue()
            # print(f"[Client] Connection with {address} is created!")
            return address
        except Exception as error:
            # print(f"[Client] RDT Connection Establishment Error: {error.with_traceback()}")
            self.socket.close()

    def udt_send(self, address, data, SEQ_num, ACK_num):
        sndpkt = RDTHeader(0, 0, 0, SEQ_num, ACK_num, len(data), 0, data, 0)
        sndpkt.set_source_address(self.address, self.port)
        sndpkt.set_target_address(address[0], address[1])
        sndpkt.checksum_cal()
        self.socket.sendto(sndpkt.to_bytes(), address)
        # print(f"[{(self.address, self.port)}] Message sent.\n {sndpkt} \n End Packet.\n")
        return time.time()  # Start Timer

    def udt_send_t(self, address, data, ACK, SEQ_num, ACK_num, seq_id) -> None:
        sndpkt = RDTHeader(0, 0, ACK, SEQ_num, ACK_num, len(data), 0, data, 0)
        sndpkt.set_source_address(self.address, self.port)
        sndpkt.SEG_SERIAL = seq_id
        sndpkt.set_target_address(address[0], address[1])
        sndpkt.checksum_cal()
        self.socket.sendto(sndpkt.to_bytes(), address)

    def corrupt(self, rcvpkt):
        rcv_checksum = rcvpkt.CHECKSUM
        # print(f"Received packet checksum: {rcvpkt.CHECKSUM}")
        rcvpkt.checksum_cal()
        # print(f"Calculated packet checksum: {rcvpkt.CHECKSUM}")
        if rcv_checksum == rcvpkt.CHECKSUM:
            return False
        else:
            return True

    def send(self, address, data=None, tcpheader=None):
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
        data_seg = [data[i:i + DATA_DIVIDE_LENGTH] for i in
                    range(0, len(data), DATA_DIVIDE_LENGTH)]  # Data segmentation
        controller = congestion.CongestionController()
        timeoutInterval = controller.timeoutInterval
        sampleRTT = 0
        timer = {}

        SEQ_num = 0  # Byte Stream "number" of the first byte in the data
        ACK_num = 0  # Byte Stream "number" of the next byte expected by the sender
        last_ACK_num = 0
        seq = 0
        wnd = controller.cwnd

        corrupt_cnt = 0
        timeout_cnt = 0
        state_0_time = 0
        state_0_cnt = 0
        state_1_time = 0
        state_1_cnt = 0
        state_2_time = 0
        state_2_cnt = 0
        state_2_cnt_hit = 0
        state_3_time = 0
        state_3_cnt = 0
        state_3_cnt_hit = 0
        send_start = time.time()

        state = send_state.WAIT_FOR_CALL_0

        is_acked = [False for _ in range(len(data_seg))]
        un_acked = [i for i in range(len(data_seg))]

        while address in self.conn.keys():
            wnd = controller.cwnd
            if state == send_state.WAIT_FOR_CALL_0:
                state_0_cnt += 1
                # start_time = time.time()
                while wnd != 0 and len(un_acked) != 0:
                    seq = un_acked.pop(0)
                    ACK_num = SEQ_num + len(data_seg[seq])
                    self.udt_send_t(address, data_seg[seq], 0, SEQ_num, ACK_num, seq)
                    SEQ_num += len(data_seg[seq])
                    wnd -= 1
                state = send_state.WAIT_FOR_ACK_0
                # state_0_time += time.time() - start_time
            elif state == send_state.WAIT_FOR_ACK_0:
                # start_time = time.time()
                state_1_cnt += 1
                rcvpkt = self.conn[address].get()
                # print(f"[Sender] Get seg serial {rcvpkt.SEG_SERIAL}")
                if(rcvpkt.SEG_SERIAL == len(data_seg) - 1):
                    print("break")
                    break
                # if rcvpkt.ACK_num == last_ACK_num:
                #     controller.duplicate_ack()
                # state_2_cnt_hit += 1
                # timeout_cnt += 1
                if self.corrupt(rcvpkt) or rcvpkt.ACK != 0:
                    # print("[Sender] Corrupted ACK packet.")
                    self.udt_send_t(address, data_seg[rcvpkt.SEG_SERIAL], 0, SEQ_num, ACK_num, rcvpkt.SEG_SERIAL)
                    # corrupt_cnt += 1
                elif rcvpkt.ACK == 0:
                    # print("[Sender] Received ACK packet.")
                    is_acked[rcvpkt.SEG_SERIAL] = True
                    if rcvpkt.SEG_SERIAL == seq:
                        controller.update()
                        state = send_state.WAIT_FOR_CALL_0

                last_ACK_num = rcvpkt.ACK_num
                # state_2_time += time.time() - start_time
        print("[Sender] Data sent. Ready to close connection.")
        end_time = time.time()
        self.close_conn_active(address, SEQ_num, ACK_num)
        close_conn_time = time.time() - end_time
        print(f"================Sender Information======================\n"
              f"send time: {time.time() - send_start}\n"
              f"State wait for call 0 cnt: {state_0_cnt}\n"
              f"State wait for ack 0 cnt: {state_1_cnt}\n"
              f"Close connection active time: {close_conn_time}")
        return

    def send_congestion(self, address, data=None, tcpheader=None):
        data_seg = [data[i:i + DATA_DIVIDE_LENGTH] for i in
                    range(0, len(data), DATA_DIVIDE_LENGTH)]  # Data segmentation
        timer = None
        SEQ_num = 0  # Byte Stream "number" of the first byte in the data
        ACK_num = 0  # Byte Stream "number" of the next byte expected by the sender

        def ByteId(x) -> int:
            return x // DATA_DIVIDE_LENGTH

        is_acked = [False for _ in range(len(data_seg))]
        un_acked = [i for i in range(len(data_seg))]
        ctrl = congestion.CongestionController()

        while len(un_acked) != 0:
            cwnd = ctrl.cwnd
            st = []
            with self.packets_lock:
                self.packets["DATA"][address] = []
            RTT = time.time()
            while cwnd != 0 and len(un_acked) != 0:
                seq = un_acked.pop(0)
                st.append(seq)
                SEQ_num = seq * DATA_DIVIDE_LENGTH
                ACK_num = SEQ_num + len(data_seg[seq])
                self.udt_send_t(address, data_seg[seq], SEQ_num, ACK_num)
                cwnd -= 1
            probe_time = 0
            while True:
                probe_time += 1
                if probe_time != 256:
                    continue
                probe_time = 0
                with self.packets_lock:
                    if len(self.packets["DATA"][address]) != 0:
                        break
            RTT = time.time() - RTT
            time.sleep(max(0, ctrl.timeoutInterval - RTT))
            ctrl.set_timeout_interval(RTT)
            with self.packets_lock:
                q = self.packets["DATA"][address]
            for pkt in q:
                is_acked[ByteId(pkt.ACK_num - 1)] = True
            st.reverse()
            for i in st:
                if not is_acked[i]:
                    un_acked.insert(0, i)
            if len(q) == ctrl.cwnd:
                ctrl.update(ctrl.cwnd)
            else:
                ctrl.timeout()

        self.close_conn_active(address, SEQ_num, ACK_num)
        return

    def recv(self, address):
        """
        You should implement the basic logic for receiving data in this function, and
        verify the data. When corrupted or missing data packets are detected, a request
        for retransmission should be sent to the other party.

        This function should be blocking.
        """
        timer = None
        SEQ_num = 0
        ACK_num = 0
        state = receive_state.WAIT_FOR_0_FROM_BELOW
        data_received = []

        state_0_time = 0
        state_0_cnt = 0
        state_0_cnt_hit = 0
        state_1_time = 0
        state_1_cnt = 0
        state_1_cnt_hit = 0

        send_start = time.time()

        while True and address in self.conn.keys():
            with self.packets_lock:
                if address in self.packets["FIN_ACK"].keys():
                    print("Received FIN ACK signal")
                    break
                # time.sleep(0.1)=
                # print("[Receiver] Wait for 0 from below")
                # start_time = time.time()
            try:
                rcvpkt = self.conn[address].get(timeout=self.timeout)
            except queue.Empty:
                continue
            # print(f"[Receiver] Get seg serial {rcvpkt.SEG_SERIAL}")
            # state_0_cnt += 1
            if self.corrupt(rcvpkt) or rcvpkt.ACK != 0:
                # print("Corrupted DATA packet.")
                pass
            elif rcvpkt.ACK == 0:
                # print("Received non-corrupted packet.")
                # state_0_cnt_hit += 1
                SEQ_num = rcvpkt.ACK_num
                ACK_num = rcvpkt.SEQ_num + len(rcvpkt.PAYLOAD.encode())
                self.udt_send_t(address, rcvpkt.PAYLOAD, 0, SEQ_num, ACK_num, rcvpkt.SEG_SERIAL)
                data_received.append(rcvpkt)
                # state_0_time += time.time() - start_time
        print("[Receiver] Data received. Ready to close connection.")
        print(f"================Receiver Information======================\n"
              f"send time: {time.time() - send_start}\n"
              f"State wait for call 0 cnt: {state_0_cnt}\n")
        self.close_conn_passive(address, SEQ_num, ACK_num)
        data_received = sorted(data_received, key=lambda pkt: pkt.SEG_SERIAL)
        data_received = [pkt.PAYLOAD.encode() for pkt in data_received]
        return data_received

    def recv_congestion(self, address):
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
                self.packets["DATA"][address] = []
            for pkt in q:
                if self.corrupt(pkt):
                    continue
                self.udt_send_t(address, pkt.PAYLOAD, pkt.ACK_num, pkt.ACK_num)
                pkt_recv[pkt.SEQ_num] = pkt.PAYLOAD.encode()
        self.close_conn_passive(address, SEQ_num, ACK_num)
        return [byte for byte in pkt_recv.values()]

    def close_conn_active(self, address, SEQ_num, ACK_num):
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
            if address in self.conn.keys():
                # Send FIN ACK
                message_FIN_ACK = send_FIN_ACK(address, SEQ_num, ACK_num)
                self.socket.sendto(message_FIN_ACK.to_bytes(), address)
                # print(f"[Sender] Message FIN_ACK sent.\n {message_FIN_ACK}")

                # Receive ACK
                ack_answer = None
                while ack_answer is None:
                    # time.sleep(0.25)
                    try:
                        with self.packets_lock:
                            if address in self.packets["ACK"].keys():
                                ack_answer = self.packets["ACK"].pop(address)
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACK.to_bytes(), address)
                # print(f"[Sender] Received ACK answer.\n {ack_answer}")

                # Receive FIN ACK
                fin_ack_answer = None
                while fin_ack_answer is None:
                    # time.sleep(0.25)
                    try:
                        with self.packets_lock:
                            if address in self.packets["FIN_ACK"].keys():
                                fin_ack_answer = self.packets["FIN_ACK"].pop(address)
                    except socket.timeout:
                        self.socket.sendto(message_FIN_ACK.to_bytes(), address)
                # print(f"[Sender] Received FIN_ACK answer.\n {fin_ack_answer}")

                # Send ACK
                message_ACK = send_ACK(address, fin_ack_answer.ACK_num, fin_ack_answer.SEQ_num + 1)
                self.socket.sendto(message_ACK.to_bytes(), address)
                # print(f"[Sender] Send ACK message.\n {message_ACK}")

                # Close connection
                with self.conn_lock:
                    self.conn.pop(address)
                # print(f"[Sender] Connection to {address} closed. Current active connections are: {self.conn.keys()}")
                return
        except Exception as error:
            # print(f"[Sender] RDT 4-way handshake close {address} connection failed with {error}")
            self.socket.close()

    def close_conn_passive(self, address, SEQ_num, ACK_num):
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
            with self.packets_lock:
                if address in self.packets["FIN_ACK"].keys():
                    fin_ack_answer = self.packets["FIN_ACK"].pop(address)
            # print(f"[Receiver] Received FIN_ACK answer.\n {fin_ack_answer}")

            # Send ACK
            message_ACK = send_ACK(address, fin_ack_answer.ACK_num, fin_ack_answer.SEQ_num + 1)
            self.socket.sendto(message_ACK.to_bytes(), address)
            # print(f"[Receiver] Message ACK sent.\n {message_ACK}")

            # Send FIN ACK
            message_FIN_ACK = send_FIN_ACK(address, SEQ_num, ACK_num)
            self.socket.sendto(message_FIN_ACK.to_bytes(), address)
            # print(f"[Receiver] Message FIN_ACK sent.\n {message_FIN_ACK}")

            # Receive ACK
            ack_answer = None
            while ack_answer is None:
                # time.sleep(0.25)
                try:
                    with self.packets_lock:
                        if address in self.packets["ACK"].keys():
                            ack_answer = self.packets["ACK"].pop(address)
                except socket.timeout:
                    self.socket.sendto(message_FIN_ACK.to_bytes(), address)
            # print(f"[Receiver] Received ACK answer.\n {ack_answer}")

            # Close connection
            with self.conn_lock:
                self.conn.pop(address)
            # print(f"[Receiver] Connection from {address} closed. Current active connections are {self.conn.keys()}")
            return
        except Exception as error:
            # print(f"[Receiver] RDT 4-way handshake close {address} connection failed with {error}")
            self.socket.close()

    def close(self):
        """
        Close current RDT connection.
        You should follow the 4-way-handshake, and then the RDT connection will be terminated.
        """
        try:
            for address, state in self.conn.items():
                self.close_conn_active(address, 0, 1)
            self.socket.close()
            self.status = 0
        except Exception as error:
            print(f"[Client] RDT Connection Closd failed with: {error}")
            self.socket.close()
