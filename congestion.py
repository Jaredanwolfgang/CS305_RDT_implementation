import threading
class state(enumerate):
    SLOW_START = 1
    CONGESTION_AVOIDANCE = 2
    FAST_RECOVERY = 3
class CongestionController():
    def __init__(self):
        self.state = state.SLOW_START
        self.cwnd = 512
        self.ssthresh = 512
        self.dup_ack = 0
        self.estimatedRTT = 0.2
        self.devRTT = 0
        self.sampleRTT = 0
        self.timeoutInterval = 1
    def update(self):
        if self.state == state.SLOW_START:
            self.cwnd *= 2
            if self.cwnd >= self.ssthresh:
                self.state = state.CONGESTION_AVOIDANCE
        elif self.state == state.CONGESTION_AVOIDANCE:
            self.cwnd += 1
        elif self.state == state.FAST_RECOVERY:
            self.cwnd = self.ssthresh
            self.state = state.CONGESTION_AVOIDANCE
    def duplicate_ack(self):
        self.dup_ack += 1
        if self.dup_ack == 3:
            self.ssthresh = self.cwnd / 2
            self.cwnd = self.ssthresh + 3
            self.state = state.FAST_RECOVERY
    def timeout(self):
        self.ssthresh = self.cwnd / 2
        self.cwnd = 8
        self.state = state.SLOW_START
    def set_timeout_interval(self, sampleRTT): # Sample RTT comes from the timer for each messages sent
        self.sampleRTT = sampleRTT
        self.estimatedRTT = (1 - 0.125) * self.estimatedRTT + 0.125 * sampleRTT
        self.devRTT = (1 - 0.25) * self.devRTT + 0.25 * abs(sampleRTT - self.estimatedRTT)
        self.timeoutInterval = self.estimatedRTT + 4 * self.devRTT
    def get_cwnd(self):
        return self.cwnd
    def get_state(self):
        return self.state
    def get_ssthresh(self):
        return self.ssthresh