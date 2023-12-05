import socket
import time


# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

# Slow Start Threshhold
SSTHRESH = 64

# total packets to send - DYNAMIC
CWND = 1

# read data
with open('send.txt', 'rb') as f:
    data = f.read()
 
# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # Start counter for throughput computation
    start_time = time.time()
    # Keeps track of overall per-packet_delay time for each packet
    per_packet_delay = 0
    # Keep track of number of packet sent and that we received an 'ack' for
    packet_count = 0

    # bind the socket to a OS port
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)
    
    # start sending data from 0th sequence
    seq_id = 0

    # Keep track of triple duplicates and exceeding sstresh
    reached_limit = False
    while seq_id < len(data):
        
        # create messages
        messages = []
        acks = {}
        
        missing_packet_id = -1

        seq_id_tmp = seq_id
        packet_delay_start = time.time()
        for i in range(CWND):
            # construct messages
            # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            messages.append((seq_id_tmp, message))

            # move seq_id tmp pointer ahead
            seq_id_tmp += MESSAGE_SIZE

        # send messages
        for _, message in messages:
            udp_socket.sendto(message, ('localhost', 5001))
        
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                # Updating packet delay
                per_packet_delay += time.time() - packet_delay_start
                packet_count += 1

                # For debugging purposes
                print(ack_id, ack[SEQ_ID_SIZE:], seq_id_tmp)

                # Keeps track of the most recent requested packet from receiver
                missing_packet_id = ack_id

                # Update scks dictionary to check for triple duplicates
                if ack_id in acks:
                    acks[ack_id] += 1

                else:
                    acks[ack_id] = 1

                # If ack_id exceeds seq_temp_id or end of window
                # increament CWND and break
                if ack_id >= seq_id_tmp:
                    inc_size = (ack_id - seq_id) // MESSAGE_SIZE

                    if reached_limit:
                        CWND += inc_size
                    else:
                        CWND *= inc_size * 2

                    # Adjusting SSTHRESH after the slow start phase
                    if CWND >= SSTHRESH:
                        reached_limit = True
                        SSTHRESH = CWND // 2
                        CWND = SSTHRESH

                    # move sequence id forward 
                    seq_id += MESSAGE_SIZE * CWND

                    print("CWND: ", CWND, "Inc: ", inc_size)
                    break
                    
                # Handles case of a triple duplicate
                if acks[ack_id] % 3 == 0:
                    SSTHRESH = CWND // 2
                    CWND += SSTHRESH + 3
                    
                    reached_limit = True

                    # Sending potentially lost packet
                    _, packet_message = messages[ack_id // MESSAGE_SIZE]
                    udp_socket.sendto(packet_message, ('localhost', 5001))
                print("CWND2: ", CWND)
            except socket.timeout:
                # no ack received, resend unacked messages
                # Sends packets from requested ack_id to end of window size
                reached_limit = False
                print((missing_packet_id) // MESSAGE_SIZE)
                _, message = messages[missing_packet_id // MESSAGE_SIZE]
                udp_socket.sendto(message, ('localhost', 5001))
                        
    # Computing throughput
    throughput = len(data) / (time.time() - start_time)

    # Computing packet delay avg.
    per_packet_delay /= packet_count

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


    print("Report")
    print("Throughput:               %.2f" % throughput)
    print("Average Per-packet delay: %.2f" % per_packet_delay)
    print("Performance metric:       %.2f" % (throughput / per_packet_delay))
