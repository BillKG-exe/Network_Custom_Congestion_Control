import socket
import time
#from datetime import datetime

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

def send_stop_wait_protocol():
    # read data
    with open('file.mp3', 'rb') as f:
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
        udp_socket.bind(("localhost", 5000))
        udp_socket.settimeout(1)
        
        # start sending data from 0th sequence
        seq_id = 0
        while seq_id < len(data):
            # construct message
            # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
            message = int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + data[seq_id : seq_id + MESSAGE_SIZE]
            
            # send message out
            udp_socket.sendto(message, ('localhost', 5001))

            # Starting the counter for per packet delay computation
            pp_start = time.time()
            
            # wait for acknowledgement
            while True:
                try:
                    # wait for ack
                    ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                    # Adding delay time to calculate the average per-packet delay
                    per_packet_delay += time.time() - pp_start
                    
                    # extract ack id
                    ack_id, ack_res = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big'), ack[SEQ_ID_SIZE:].decode()
                    #print(ack_id, ack_res)
                    
                    # ack id == sequence id, move on
                    if ack_id == seq_id + 1020 or ack_id == len(data):
                        break
                except socket.timeout:
                    # no ack, resend message
                    udp_socket.sendto(message, ('localhost', 5001))
                    
            # Increment packets count by one after receiving 'ack'
            packet_count += 1
            # move sequence id forward
            seq_id += MESSAGE_SIZE
        
        # Computing throughput
        throughput = len(data) / (time.time() - start_time)

        # send final closing message
        udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big')+ b"", ('localhost', 5001))

        response = []
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                response.append(ack[SEQ_ID_SIZE:].decode())

                if "fin" in response and "ack" in response:
                    #udp_socket.sendto(b"==FINACK==", ('localhost', 5001))
                    break
            except socket.timeout:
                udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big')+ b"", ('localhost', 5001))

        udp_socket.sendto(int.to_bytes(len(data), 4, signed=True, byteorder='big') + b"==FINACK==", ('localhost', 5001))

        # Computing average per-packet delay
        per_packet_delay /= packet_count 

        return throughput, per_packet_delay
    

def evaluate_performance():
    avg_throughput = 0
    avg_per_packet_delay = 0

    throughput, delay = send_stop_wait_protocol()

    avg_throughput += throughput
    avg_per_packet_delay += delay
        
    # Print final report
    print("%.2f," % avg_throughput)
    print("%.2f," % avg_per_packet_delay)
    print("%.2f" % (avg_throughput / avg_per_packet_delay))


if __name__ == "__main__":
    evaluate_performance()
