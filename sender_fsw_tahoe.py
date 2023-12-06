import socket
import time
import math

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send (dynamic cwnd)
WINDOW_SIZE = 1
# Slow Start Threshhold
SSTHRESH = 64

# read data
with open('file.mp3', 'rb') as f:
    data = f.read()

# PACKETIZE DATA
# start sending data from 0th sequence
seq_id = 0
# create messages
messages = []
# how many total messages to send
num_messages = math.ceil(len(data)/MESSAGE_SIZE)
# store all messages to be sent in messages
for i in range(num_messages):
    # construct messages
    # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
    message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id : seq_id + MESSAGE_SIZE]
    messages.append((seq_id, message))
    # move seq_id tmp pointer ahead
    seq_id += MESSAGE_SIZE
 
# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # Starting timer for through put computation
    throughput_start_time = time.time()
    # Variable to compute and record all packet delays
    packet_delays = []

    # bind the socket to a OS port
    udp_socket.bind(("localhost", 5000))
    # dynamically change timeout (every time a packet is timeout, we double it)
    timeout = 1
    udp_socket.settimeout(timeout)

    # lower bound of window (increments by 1 for every packet)
    window_start = 0
    # upper bound of window (starts at 1 as long as there are messages)
    window_end = min(WINDOW_SIZE, num_messages)
    # number of dup acks (when reaches 3, fast restransmit and reset to 0)
    dup_ack = 0

    # when window_end is the same as num_messages, we have sent and acked all messages
    while window_end < num_messages:
        # send first message
        for sid, message in messages[window_start:window_end]:
            print("Sending", sid)
            # start timer for per packet delay before sending packets
            packet_delays.append(time.time())
            udp_socket.sendto(message, ('localhost', 5001))
        
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                # record the time once we receive the ack
                packet_end_time = time.time()

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                print(ack_id, ack[SEQ_ID_SIZE:])
                
                # slide window if ack_id more than start of window (some new packets got acked)
                if ack_id > (window_start * MESSAGE_SIZE):
                    # we got a new ack, reset timeout to 1
                    timeout = 1
                    udp_socket.settimeout(timeout)

                    # update window start pointers
                    window_start_old = window_start
                    window_start = math.ceil(ack_id/MESSAGE_SIZE)

                    # UPDATE CWND
                    if(WINDOW_SIZE < SSTHRESH):
                        # SLOW START
                        WINDOW_SIZE += window_start - window_start_old
                        if(WINDOW_SIZE > SSTHRESH):
                            WINDOW_SIZE = SSTHRESH
                    else:
                        # CONGESTION AVOIDANCE
                        WINDOW_SIZE += 1

                    # update window end pointers  
                    window_end_old = window_end
                    window_end = min(window_start + WINDOW_SIZE, num_messages)
                    # HAVE TO MAKE SURE THE WINDOW END DOESNT MOVE BACKWARDS AFTER WINDOW RESIZE
                    if (window_end < window_end_old):
                        window_end = window_end_old

                    # record delays for messages that just acknowledged
                    for i in range(window_start_old, window_start):
                        packet_delays[i] = packet_end_time - packet_delays[i]

                    # send messages that just appeared in window
                    for sid, message in messages[window_end_old:window_end]:
                        print("Sending (after window slide)", sid)
                        # start timer for per packet delay before sending new packets
                        packet_delays.append(time.time())
                        udp_socket.sendto(message, ('localhost', 5001))

                # if ack_id = window_start (cant be less), then we got a dup ack
                else:
                    dup_ack += 1
                    if(dup_ack == 3):
                        # SET SSTHRESH TO HALF OF CWND
                        SSTHRESH = max(WINDOW_SIZE // 2, 1)
                        # RESET CWND TO 1
                        WINDOW_SIZE = 1
                        # fast retransmit
                        print("Resending (fast retransmit)", messages[window_start][0])
                        udp_socket.sendto(messages[window_start][1], ('localhost', 5001))
                        dup_ack = 0

                # break if we have sent all data (will also break outer while, window_end = num_messages)
                if(ack_id >= len(data)):
                    break

            except socket.timeout:
                # SET SSTHRESH TO HALF OF CWND
                SSTHRESH = max(WINDOW_SIZE // 2, 1)
                # RESET CWND TO 1
                WINDOW_SIZE = 1
                # double the timeout
                timeout *= 2
                udp_socket.settimeout(timeout)
                # no ack received, resend first msg in window
                print("Resending (timeout)", messages[window_start][0])
                udp_socket.sendto(messages[window_start][1], ('localhost', 5001))

                
    # Computing throughput
    throughput = len(data) / (time.time() - throughput_start_time)
    # Computing average per packet delay
    avg_per_packet_delay = sum(packet_delays) / len(packet_delays)

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


# Print final report
print("Report")
print("Throughput:               %.2f," % throughput)
print("Average Per-packet delay: %.2f," % avg_per_packet_delay)
print("Performance metric:       %.2f" % (throughput / avg_per_packet_delay))