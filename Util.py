class Packet:
    def __init__(self, pid, message):
        self.pid = pid
        self.message = message
        self.sentStatus = False
        self.recvStatus = False


def wereAllRecv(packets):
    for packet in packets:
        if packet.recvStatus == False:
            return False
    
    return True