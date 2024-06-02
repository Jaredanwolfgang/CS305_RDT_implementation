class RDTHeader():
    def __init__(self, SYN: int = 0, FIN: int = 0, ACK: int = 0, SEQ_num: int = 0, ACK_num: int = 0, LEN: int = 0, CHECKSUM: int = 0, PAYLOAD = None, RWND: int = 0)  -> None:
        self.test_case = 0                      # Indicate the test case that will be used
        self.SYN = SYN                          # 1 bytes
        self.FIN = FIN                          # 1 bytes
        self.ACK = ACK                          # 1 bytes
        self.SEQ_num = SEQ_num                  # 4 bytes
        self.ACK_num = ACK_num                  # 4 bytes
        self.LEN = LEN                          # 4 bytes
        self.CHECKSUM = CHECKSUM                # 2 bytes
        if isinstance(PAYLOAD, str):
            self.PAYLOAD = PAYLOAD
        elif isinstance(PAYLOAD, bytes):
            self.PAYLOAD = PAYLOAD.decode()
        else:
            self.PAYLOAD = ""
        # self.CWND = CWND                      # Congestion window size 4 bytes
        self.RWND = RWND                        # Notification window size 4 bytes
        self.ID = 0                             # 2 bytes, Identification Field for any file (Having the same ID means the same file)
        self.SEG_SERIAL = 0                     # 2 bytes, When conducting data segment transmission, the serial number of the segment
        self.Reserved = 0                       # 4 bytes, Reserved field
        
        self.Source_address = [127, 0, 0, 1, 12334] # Souce ip and port: each segment of IP takes 1 byte, the port takes 2 bytes
        self.Target_address = [127, 0, 0, 1, 12345] # Target ip and port
    
    def checksum_cal(self):
        # Step 1:
        # Join all bytes data together 
        # (In the order of SYN, FIN, ACK, SEQ_num, 
        # ACK_num, LEN, RWND, CHECKSUM, Reserved, PAYLOAD.).
        self.CHECKSUM = 0
        if isinstance(self.PAYLOAD, str):
            sum_data = self.SYN.to_bytes(1, 'big') + self.FIN.to_bytes(1, 'big') + self.ACK.to_bytes(1, 'big') + \
                    self.SEQ_num.to_bytes(4, 'big') + self.ACK_num.to_bytes(4, 'big') + self.LEN.to_bytes(4, 'big') + \
                    self.RWND.to_bytes(4, 'big') + self.CHECKSUM.to_bytes(2, 'big') + self.ID.to_bytes(2, 'big') + \
                    self.SEG_SERIAL.to_bytes(2, 'big') + self.Reserved.to_bytes(4, 'big') + \
                    self.PAYLOAD.encode()
        else:
            sum_data = self.SYN.to_bytes(1, 'big') + self.FIN.to_bytes(1, 'big') + self.ACK.to_bytes(1, 'big') + \
                    self.SEQ_num.to_bytes(4, 'big') + self.ACK_num.to_bytes(4, 'big') + self.LEN.to_bytes(4, 'big') + \
                    self.RWND.to_bytes(4, 'big') + self.CHECKSUM.to_bytes(2, 'big') + self.ID.to_bytes(2, 'big') + \
                    self.SEG_SERIAL.to_bytes(2, 'big') + self.Reserved.to_bytes(4, 'big')
        
        # Step 2:
        # Didvide the result into 2-byte segments, 
        # with each 2-byte segment forming a 16-bit value. 
        # If there is a single byte of data at the end, 
        # add an extra byte of 0 to form a 2-byte segment.
        data_seg = [sum_data[i:i+2] for i in range(0, len(sum_data), 2)]
        if len(data_seg[-1]) == 1:
            data_seg[-1] += b'\x00'
        
        # Step 3:
        # Sum all the 16-bit values to obtain a 32-bit value.
        sum_data = [int.from_bytes(i, 'big') for i in data_seg]
        sum_data = sum(sum_data)
        
        # Step 4:
        # Add the high 16 bits and low 16 bits of the 32-bit 
        # value to get a new 32-bit value. If the new 32-bit 
        # value exceeds 0xFFFF, add the high 16 bits and low 
        # 16 bits of the new value again.
        sum_data = (sum_data & 0xFFFF) + (sum_data >> 16)
        while(sum_data > 0xFFFF):
            sum_data = (sum_data & 0xFFFF) + (sum_data >> 16)
        
        # Step 5:
        # Take the 1's complement of the result obtained in 
        # the previous step to obtain the checksum value, 
        # and store it in the checksum field of the data.
        self.CHECKSUM = 0xFFFF - sum_data
        return self.CHECKSUM
    
    def set_test_case(self, test_case):
        self.test_case = test_case
        
    def set_source_address(self, ip, port):
        self.Source_address = [int(i) for i in ip.split('.')]
        self.Source_address.append(port)
    
    def set_target_address(self, ip, port):
        self.Target_address = [int(i) for i in ip.split('.')]
        self.Target_address.append(port)

    def set_seq_number(self, seq_number):
        self.SEQ_num = seq_number
    
    def to_bytes(self):
        test_case = self.test_case.to_bytes(1, 'big')
        Source_address = self.Source_address[0].to_bytes(1, 'big') + self.Source_address[1].to_bytes(1, 'big') + \
                            self.Source_address[2].to_bytes(1, 'big') + self.Source_address[3].to_bytes(1, 'big') + \
                            self.Source_address[4].to_bytes(2, 'big')
                            
        Target_address = self.Target_address[0].to_bytes(1, 'big') + self.Target_address[1].to_bytes(1, 'big') + \
                            self.Target_address[2].to_bytes(1, 'big') + self.Target_address[3].to_bytes(1, 'big') + \
                            self.Target_address[4].to_bytes(2, 'big')
        
        SYN = self.SYN.to_bytes(1, 'big')
        FIN = self.FIN.to_bytes(1, 'big')
        ACK = self.ACK.to_bytes(1, 'big')
        SEQ_num = self.SEQ_num.to_bytes(4, 'big')
        ACK_num = self.ACK_num.to_bytes(4, 'big')
        LEN = self.LEN.to_bytes(4, 'big')
        RWND = self.RWND.to_bytes(4, 'big')
        
        self.checksum_cal()
        CHECKSUM = self.CHECKSUM.to_bytes(2, 'big')
        PAYLOAD = self.PAYLOAD.encode()
        ID = self.ID.to_bytes(2, 'big')
        SEG_SERAIL = self.SEG_SERIAL.to_bytes(2, 'big')
        Reserved = self.Reserved.to_bytes(4, 'big')
        
        return b''.join([test_case, Source_address, Target_address, SYN, FIN, ACK, SEQ_num, ACK_num, LEN, RWND, CHECKSUM, ID, SEG_SERAIL, Reserved, PAYLOAD])

    def from_bytes(self, data):
        self.test_case = data[0]
        Source_address = []
        for i in range(4):
            Source_address.append(data[i + 1])
        Source_address.append(int.from_bytes(data[5:7], 'big'))
        self.Source_address = Source_address
        
        Target_address = []
        for i in range(4):
            Target_address.append(data[i + 7])
        Target_address.append(int.from_bytes(data[11:13], 'big'))
        self.Target_address = Target_address
            
        self.SYN = data[13]
        self.FIN = data[14]
        self.ACK = data[15]
        self.SEQ_num = int.from_bytes(data[16:20], 'big')
        self.ACK_num = int.from_bytes(data[20:24], 'big')
        self.LEN = int.from_bytes(data[24:28], 'big')
        self.RWND = int.from_bytes(data[28:32], 'big')
        self.CHECKSUM = int.from_bytes(data[32:34], 'big')
        self.ID = int.from_bytes(data[34:36], 'big')
        self.SEG_SERIAL = int.from_bytes(data[36:38], 'big')
        self.Reserved = int.from_bytes(data[38:42], 'big')
        self.PAYLOAD = data[42:].decode()
        return self

    def __str__(self) -> str:
        return f"SYN: {self.SYN} FIN: {self.FIN} ACK: {self.ACK}\n SEQ_num: {self.SEQ_num} ACK_num: {self.ACK_num} LEN: {self.LEN}\n CHECKSUM: {self.CHECKSUM} RWND: {self.RWND}\n PAYLOAD: {self.PAYLOAD}\n Source_address: {self.Source_address}\n Target_address: {self.Target_address}"
    
    def __repr__(self) -> str:
        return self.__str__()

