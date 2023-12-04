import socket
import time
from Util import Packet

# Constants values 
PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE


def send_reno_protocol():
    # Read data from file
    with open('send.txt', 'rb') as f:
        data = f.read()

    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        # cwind and sstresh initial values
        CONGESTION_WINDOW_SIZE = 1
        SSTRESH = 64

        # CHecks if we exceeded, received triple duplicate or timeout
        reached_limit = False

        # Staring timer for through put computation
        start_time = time.time()

        # Bind the socket to an OS port
        udp_socket.bind(("localhost", 5000))
        udp_socket.settimeout(1)

        # Creating packets for the file data to be sent
        seq_id = 0
        window = []
        while seq_id < len(data):
            # Creates packet with seq_id and message
            # Append the packet to the window store
            window.append(Packet(int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True), data[seq_id:seq_id + MESSAGE_SIZE]))
            seq_id += MESSAGE_SIZE

        WINDOW_LENGTH = len(window)
        
        # Lower bound of sliding window
        window_base = 0
        # Upper bound of sliding window
        window_top = CONGESTION_WINDOW_SIZE

        # Variable to computer average per packet delay
        per_packet_delay = 0

        # Keeps track of the acknolegemnts from receiver
        acks = {}

        while window_base < len(window):
            # Send packets within the window
            # window_base + WINDOW_SIZE -> make sure that window does not exceed
            # the window size of 100 packets
            packet_delay_start = time.time()
            for i in range(window_base, min(window_top, (window_base + CONGESTION_WINDOW_SIZE), len(window))):
                #print("Index: %d window base: %d window top: %d win base+top: %d len(window): %d" % (i, window_base, window_top, window_base+WINDOW_SIZE, len(window)))
                udp_socket.sendto((window[i].pid + window[i].message), ('localhost', 5001))
                window[i].sentStatus = True

            
            # Wait for acknowledgments
            while True:
                try:
                    ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                    if ack_id in acks:
                        acks[ack_id] += 1
                    else:
                        acks[ack_id] = 1
                
                    if acks[ack_id] == 3:
                        SSTRESH = CONGESTION_WINDOW_SIZE // 2
                        CONGESTION_WINDOW_SIZE = SSTRESH + 3
                        reached_limit = True
                    
                    per_packet_delay += time.time() - packet_delay_start
                    #print(ack_id, ack[SEQ_ID_SIZE:].decode())

                    # Update window pointers
                    while window and int.from_bytes(window[0].pid, byteorder='big') < ack_id:
                        if CONGESTION_WINDOW_SIZE >= SSTRESH:
                            reached_limit = True
                            CONGESTION_WINDOW_SIZE += 1
                        elif not reached_limit:
                            CONGESTION_WINDOW_SIZE *= 2
                        else:
                            CONGESTION_WINDOW_SIZE += 1

                        window.pop(0)
                        window_top = min(window_base + CONGESTION_WINDOW_SIZE, len(window))
                    break

                except socket.timeout:
                    # Updates the cwind and sstesh in case of a timeout
                    SSTRESH = CONGESTION_WINDOW_SIZE // 2
                    CONGESTION_WINDOW_SIZE = 1
                    reached_limit = True

                    # Ensures that leading packets in thein the queue are sent  
                    for packet in window:
                        if packet.sentStatus is True:
                            udp_socket.sendto((packet.pid + packet.message), ('localhost', 5001))
                        elif packet.sentStatus is False:
                            break

        # send final closing message
        udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big')+ b"", ('localhost', 5001))

        response = []
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                response.append(ack[SEQ_ID_SIZE:].decode())

                if "fin" in response and "ack" in response:
                    break
            except socket.timeout:
                udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big')+ b"", ('localhost', 5001))

        udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big') + b"==FINACK==", ('localhost', 5001))

        # Computing throughput
        throughput = len(data) / (time.time() - start_time)
        # Computing average per packet delay
        per_packet_delay /= (WINDOW_LENGTH * 1.0)

    return throughput, per_packet_delay 

def evaluate_performance():
    avg_throughput = 0
    avg_per_packet_delay = 0

    throughput, delay = send_reno_protocol()

    avg_throughput += throughput
    avg_per_packet_delay += delay
        
    print("Report")
    print("Throughput:               %.2f" % avg_throughput)
    print("Average Per-packet delay: %.2f" % avg_per_packet_delay)
    print("Performance metric:       %.2f" % (avg_throughput / avg_per_packet_delay))

if __name__ == "__main__":
    evaluate_performance()

    """                     if current_ack is None or current_ack != ack_id:
                        current_ack = ack_id
                    elif current_ack == ack_id:
                        dup_ack += 1 """