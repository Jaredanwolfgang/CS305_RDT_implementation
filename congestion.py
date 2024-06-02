import threading


class state(enumerate):
    SLOW_START = 1
    CONGESTION_AVOIDANCE = 2
    FAST_RECOVERY = 3


class CongestionController():
    def __init__(self):
        self.state = state.SLOW_START
        self.cwnd = 1 # The number of segments that can be sent at a time
        self.ssthresh = 64
        self.dup_ack = 0
        self.lock = threading.Lock()
        self.estimatedRTT = 0
        self.devRTT = 0
        self.sampleRTT = 0
        self.timeoutInterval = 5

    def update(self, acked):
        # TCP Tahoe
        if(acked):
            # self.lock.acquire()
            if self.state == state.SLOW_START:
                self.cwnd *= 2
                if self.cwnd >= self.ssthresh:
                    self.state = state.CONGESTION_AVOIDANCE
            elif self.state == state.CONGESTION_AVOIDANCE:
                self.cwnd += 1
            elif self.state == state.FAST_RECOVERY:
                self.cwnd = self.ssthresh
                self.state = state.CONGESTION_AVOIDANCE
            # self.lock.release()
        return self.cwnd # Determine how much data segment will be sent at a time.

    def duplicate_ack(self):  # Meaning that one ACK is lost, so we need to retransmit the packet
        # self.lock.acquire()
        self.dup_ack += 1
        if self.dup_ack == 3:
            self.ssthresh = self.cwnd / 2
            self.cwnd = self.ssthresh + 3
            self.state = state.FAST_RECOVERY
        # self.lock.release()

    def timeout(self):
        # self.lock.acquire()
        self.ssthresh = self.cwnd / 2
        self.cwnd = 1
        self.state = state.SLOW_START
        # self.lock.release()

    def set_timeout_interval(self, sampleRTT):  # Sample RTT comes from the timer for each messages sent
        # self.lock.acquire()
        self.sampleRTT = sampleRTT
        self.estimatedRTT = (1 - 0.125) * self.estimatedRTT + 0.125 * sampleRTT
        self.devRTT = (1 - 0.25) * self.devRTT + 0.25 * abs(sampleRTT - self.estimatedRTT)
        self.timeoutInterval = self.estimatedRTT + 4 * self.devRTT
        # self.lock.release()

    def get_cwnd(self):
        return self.cwnd

    def get_state(self):
        return self.state

    def get_ssthresh(self):
        return self.ssthresh

    def get_timeout_interval(self):
        return self.timeoutInterval
