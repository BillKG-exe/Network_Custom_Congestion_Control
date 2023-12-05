import socket
import time

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send
WINDOW_SIZE = 100

# read data
with open('send.txt', 'rb') as f:
    data = f.read()
 
# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # Starting timer for through put computation
    start_time = time.time()
    # Variable to computer average per packet delay
    per_packet_delay = 0

    # bind the socket to a OS port
    udp_socket.bind(("localhost", 5000))
    udp_socket.settimeout(1)

    # keep track of last acknowledged packet (helps us detect dup_acks)
    last_ack = -1
    # number of dup acks (when reaches 3, fast restransmit and reset to 0)
    dup_ack = 0
    # lower bound of window
    window_start = 0
    # upper bound of window (to avoid do while, we set this first thing in while loop)
    window_end = 0

    # start sending data from 0th sequence
    seq_id = 0
    # create messages
    messages = []
    acks = {}

    num_messages = 0
    if(len(data) % MESSAGE_SIZE == 0):
        num_messages = int(len(data)/MESSAGE_SIZE)
    else:
        num_messages = int(len(data)/MESSAGE_SIZE) + 1

    for i in range(num_messages):
        # construct messages
        # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
        message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id : seq_id + MESSAGE_SIZE]
        messages.append((seq_id, message))
        acks[seq_id] = False
        # move seq_id tmp pointer ahead
        seq_id += MESSAGE_SIZE

    #change condition
    while window_end < num_messages:
        if(window_end == 0):
            window_end = min(WINDOW_SIZE, num_messages)

        packet_delay_start = time.time()
        # send messages
        for sid, message in messages[window_start:window_end]:
            print("Sending", sid)
            udp_socket.sendto(message, ('localhost', 5001))
        
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                per_packet_delay += time.time() - packet_delay_start

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                print(ack_id, ack[SEQ_ID_SIZE:])
                acks[ack_id] = True

                # slide window if ack_id more than start of window
                if ack_id > (window_start * MESSAGE_SIZE):
                    window_start = int(ack_id/MESSAGE_SIZE)
                    window_end_old = window_end
                    window_end = min(window_start + WINDOW_SIZE, num_messages)
                    # send messages that just appeared in window
                    for sid, message in messages[window_end_old:window_end]:
                        print("Sending (after window slide)", sid)
                        udp_socket.sendto(message, ('localhost', 5001))

                # fast retransmit if 3 dup acks
                if last_ack != ack_id:
                    last_ack = ack_id
                else:
                    dup_ack += 1
                    if(dup_ack == 3):
                        print("Sending (fast retransmit)", messages[window_start][0])
                        udp_socket.sendto(messages[window_start][1], ('localhost', 5001))
                        dup_ack = 0

                # check if msgs over
                if(ack_id >= len(data)):
                    break

            except socket.timeout:
                # no ack received, resend unacked messages, SHOULD I ONLY RESEND FIRST ONE?
                for sid, message in messages[window_start:window_end]:
                    if not acks[sid]:
                        print("Sending (timeout, all unacked in window)", sid)
                        udp_socket.sendto(message, ('localhost', 5001))

                

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
    per_packet_delay /= (WINDOW_SIZE * 1.0)

    avg_throughput = throughput
    avg_per_packet_delay = per_packet_delay

    print("Report")
    print("Throughput:               %.2f" % avg_throughput)
    print("Average Per-packet delay: %.2f" % avg_per_packet_delay)
    print("Performance metric:       %.2f" % (avg_throughput / avg_per_packet_delay))


