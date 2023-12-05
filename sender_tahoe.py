import socket
import time 
from Util import Packet

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
INITIAL_WINDOW_SIZE = 1
INITIAL_THRESHOLD = 64
TIMEOUT = 1

def send_tcp_tahoe_protocol():

    with open('send.txt', 'rb') as f:
        data = f.read()
    
    # create a udp socket to communicate with the receiver
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        
        start_time = time.time()

        per_packet_delay = 0

        packet_count = 0

        # bind the socket to a OS port
        udp_socket.bind(("localhost", 5000))
        udp_socket.settimeout(TIMEOUT)

        #Declare needed variables
        seq_id = 0
        cwnd = INITIAL_WINDOW_SIZE
        ssthresh = INITIAL_THRESHOLD
        last_ack = None
        dup_counter = 0

        #UNCOMMENT THE FOLOWWING ONES IF NEEDED
        # last_ack = None
        # dup_counter = 0


        while seq_id < len(data):
            
            # create messages to send based o the size of the jumping window
            window = []
            messages_sent = {}
            seq_id_tmp = seq_id
            seq_id_send = seq_id

            packet_delay_start = time.time()
            for i in range(cwnd):
                # construct messages
                # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
                #print("seq_id_tmp: " + str(seq_id_tmp))
                print("cwnd: " + str(cwnd))
                message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
                window.append((seq_id_tmp, message))
                messages_sent[seq_id_send] = False
                ## acks[seq_id_tmp] = False

                # move seq_id tmp pointer ahead
                seq_id_tmp += MESSAGE_SIZE

            # send messages
            for _, message in window:
                udp_socket.sendto(message, ('localhost', 5001))

            #calculate the expected acknoledment that indicates that all the messages were received
            expected_ack = seq_id + MESSAGE_SIZE * cwnd
            #print("printing expected calculated: " + str(expected_ack))
            
            # wait for negative_ acknowledgement
            while True:
                try:
                    # wait for ack
                    ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    
                    # extract ack id
                    ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                    print(ack_id, ack[SEQ_ID_SIZE:])
                    #print("printing expected from receiver:" + str(expected_ack))
                    ##acks[ack_id] = True

                    per_packet_delay += time.time() - packet_delay_start
                    packet_count += 1
                    
                    # all packets received, move on and increase cwnd
                    if ack_id == expected_ack:
                        if(cwnd <= ssthresh):
                            cwnd *= 2
                        else:
                            cwnd += 1
                        break

                    if ack_id >= len(data):
                        seq_id = ack_id
                        break

                    
                    if(ack_id == last_ack):
                        dup_counter += 1

                        if(dup_counter == 3):
                            ssthresh = max(cwnd // 2, 1)
                            cwnd = 1
                            dup_counter = 0
                            #FIX FOLLOWING ONE
                            ind = ack_id // MESSAGE_SIZE
                            _, message = window[ind]
                            udp_socket.sendto(message, ('localhost', 5001))
                    else:
                        dup_counter = 0
                    
                    last_ack = ack_id



                except socket.timeout:
                    # no ack received, resend unacked messages
                    for sid, message in window:
                        if sid in messages_sent and not messages_sent[sid]:
                            print("This is timeout: " + str(sid))
                            udp_socket.sendto(message, ('localhost', 5001))
                            messages_sent[sid] = True
                    
            # move sequence id forward
            #print("moving sequence id forward to: ")
            seq_id = expected_ack
            #print(seq_id)
            
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
        per_packet_delay /= packet_count

    return throughput, per_packet_delay 


def evaluate_performance():
    avg_throughput = 0
    avg_per_packet_delay = 0

    # for _ in range(10):
    throughput, delay = send_tcp_tahoe_protocol()

    avg_throughput += throughput
    avg_per_packet_delay += delay
    #     break

    # avg_throughput /= 10
    # avg_per_packet_delay /= 10
        
    print("Report")
    print("Throughput:               %.2f" % avg_throughput)
    print("Average Per-packet delay: %.2f" % avg_per_packet_delay)
    print("Performance metric:       %.2f" % (avg_throughput / avg_per_packet_delay))

if __name__ == "__main__":
    evaluate_performance()
