import time
from RUDP_protocol import RUDP

def sender():
    data = "Sample data to be sent over by the RUDP protocol" * 20  # 470 bytes
    conn = RUDP("localhost", 3000)
    conn.connect("localhost", 2000)
    conn.listen()
    data_size = 0

    start_time = time.time()

    while True:
        conn.send(data)
        data_size += len(data)
        print("sent: ", data_size, " Bytes", end="\r")
        print(
            "sent: {} Bytes - buffer: ({})".format(data_size, len(conn.senderBuffer)),
            end="\r",
        )

        if (time.time() - start_time) >= 60:
            print("\ntest finished")
            message = "end"
            conn.send(message)
            break


def receiver():
    conn = RUDP("localhost", 2000)
    conn.connect("localhost", 3000)
    conn.listen()
    time_start = time.time()
    data_size = 0
    bandwidth = 0
    while True:
        data = conn.recv()
        if data == "end":
            print("\ntest finished")
            break
        data_size += len(data)

        bandwidth = data_size / (time.time() - time_start)
        print(
            "bandwidth: {} B/s - buffer: ({})".format(
                str(bandwidth)[0:10], len(conn.receiverBuffer)
            ),
            end="\r",
        )


mode = input("mode (1 - sender, 2 - receiver): ")
if mode == "1":
    sender()
else:
    receiver()
