import builtins, hashlib, pickle, random, socket, time
from collections.abc import Hashable
from copy import deepcopy
from pprint import pprint
from threading import Lock, Thread

DEBUG_MODE = 0  # change it to false for stdout prints from protocol

def switch(val, *args, **kargs):
    if val == 1:
        builtins.print(*args, **kargs)


def print(*args, **kargs):
    if DEBUG_MODE == 1:
        switch(DEBUG_MODE, args, kargs)


class createSocketError(RuntimeError):
    def __init__(self, args):
        self.args = args


class createConnectionError(RuntimeError):
    def __init__(self, args):
        self.args = args


""" RELIABKE UDP PROTOCOL  """


class RUDP:
    bufferSize = 1500
    packetSize = 1400  # in bytes
    windowSize = 1000  # size of buffer windows
    connectionTimeout = 1  # in seconds: starting of retransmission thread
    packetLosses = 0  # in range(0, 11), 0 for no loss
    blockAndSleep = 0.00001

    def __init__(self, interface, port):
        self.interface = interface
        self.port = port
        self.sock = self.socketInit(interface, port)
        self.receiverBuffer = []
        self.senderBuffer = []
        self.sequenceNumber = 0
        self.sequenceHash = {}
        self.closeConnTime = 0
        self.statusOfConn = False
        self.senderLock = Lock()
        self.recieveSocketLock = Lock()
        self.sendSocketLock = Lock()
        self.sequenceLock = Lock()
        self.sequenceAppLock = Lock()

        # last seq number of packet transferred to application
        self.nextSequenceAppLock = self.sequenceNumber + 1

    """
    Standard socket functions for creating socket and sending/recieving data 
    with reliability helper functions called for reliable UDP transfer protocol
    """

    def socketInit(self, interface, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((interface, port))
            return sock
        except Exception as e:
            print("Eroor occured while creating socket!: ", e)

    def connect(self, interface, port):
        try:
            self.sock.connect((interface, port))
            self.statusOfConn = True
        except Exception as e:
            print("Error occured while trying to connect: ", e)

    def listen(self):
        try:
            if self.statusOfConn == False:
                raise createConnectionError("First connect to other peer.")
            listenerThread = Thread(target=self.listenerHelper)
            retransmissionThread = Thread(target=self.retransmitHelper)
            listenerThread.start()
            retransmissionThread.start()
        except Exception as e:
            print("Erro occured while listen: ", e)

    def send(self, data, blocking=True):
        try:
            if not isinstance(data, Hashable):
                raise Exception("Data object is not hashable.")
            if blocking == True:
                while self.sendNonBlockingMode(data) == False:
                    time.sleep(RUDP.blockAndSleep)
            else:
                return self.sendNonBlockingMode(data)
        except Exception as e:
            print("Error occured while sending data: ", e)

    def recv(self, blocking=True):
        try:
            if blocking == True:
                while True:
                    data = self.readHelper()
                    if data != None:
                        data = deepcopy(data)
                        return data
                    time.sleep(RUDP.blockAndSleep)
            else:
                data = self.readHelper()
                data = deepcopy(data)
                return data
        except Exception as e:
            print("Error occured while receiving data: ", e)

    def close(self):
        try:
            self.statusOfConn = False
            self.closeConnTime = time.time()
        except Exception as e:
            print("Error occured while closing connection: ", e)

    def rateOfpacketLoss(self, value):
        if value <= 10 and value >= 0:
            RUDP.packetLosses = value
        else:
            raise Exception("Value not in range. (0 - 10)")

    """
    Reliability Helper Functions over UDP protocol
    """

    def retransmitHelper(self):
        try:
            while True:
                time.sleep(RUDP.connectionTimeout)

                if self.statusOfConn == False and len(self.senderBuffer) == 0:
                    return

                with self.senderLock:
                    print("Retransmitting thread aquired the lock...")
                    for packet in self.senderBuffer:
                        time_now = time.time()
                        if (time_now - packet[2]) >= RUDP.connectionTimeout:
                            print("Retransmitting: ", packet[0])
                            self.writeHelper(packet[1], "DATA", retransmit=True)
                        # rest of the packets in the queue are yet to connectionTimeout
                        else:
                            break
                print("# packets in buffer: ", len(self.senderBuffer))
        except Exception as e:
            print("Error occured while retransmiting packets: ", e)

    def listenerHelper(self):
        try:
            if self.sock == None:
                raise createSocketError("Socket not created")

            count_ACK = 0  # counts number of acke'd packets still in sent list
            map_ACK = set()
            print("listening for datagrams at {}:".format(self.sock.getsockname()))

            while True:
                try:
                    with self.recieveSocketLock:
                        data, address = self.sock.recvfrom(RUDP.bufferSize)
                except Exception as _:
                    return

                data_recv = data
                print("client at {}".format(address))
                data_recv = pickle.loads(data_recv)
                print(data_recv)

                if data_recv["type"] == "ACK":
                    print("recv ACK for: ", data_recv["seqence_ACK"])
                    print("# packets in buffer: ", len(self.senderBuffer))
                    count_ACK += 1
                    map_ACK.add(data_recv["seqence_ACK"])

                    if count_ACK >= (RUDP.windowSize / 10) or (
                        ((time.time() - self.closeConnTime) >= 5 * RUDP.connectionTimeout)
                        and self.statusOfConn == False
                    ):
                        count_ACK = 0
                        temp_senderBuffer = []
                        with self.senderLock:
                            print("listening thread aquired lock.")
                            for packet in self.senderBuffer:
                                if packet[0] not in map_ACK:
                                    temp_senderBuffer.append(packet)
                            self.senderBuffer = temp_senderBuffer
                            map_ACK = set()

                else:
                    if data_recv["seq"] >= (
                        self.nextSequenceAppLock
                        + (RUDP.windowSize - (RUDP.windowSize / 10))
                    ):
                        # the recieved data is outside 90% of the buffer window size
                        continue

                    data = data_recv["data"]

                    if hashlib.md5(pickle.dumps(data)).hexdigest() != data_recv["hash"]:
                        # check if any inconsistant data has arrived
                        print("inconsistent data received")
                        continue

                    if (
                        len(self.receiverBuffer) < RUDP.windowSize
                    ) or self.sequenceHash.get(data_recv["seq"]) != None:
                        print("sending ACK for: ", data_recv["seq"])
                        data_snd = {}
                        data_snd["seqence_ACK"] = data_recv["seq"]
                        self.writeHelper(data_snd, "ACK")

                    if (
                        len(self.receiverBuffer) < RUDP.windowSize
                        and self.sequenceHash.get(data_recv["seq"]) == None
                    ):
                        self.receiverBuffer.append((data_recv["seq"], data_recv))
                        self.sequenceHash[data_recv["seq"]] = True

                    else:
                        print("data rejected: data already recieved or buffer full")
        except Exception as e:
            print("Error occured in reliable listener: ", e)

    def readHelper(self):
        try:
            if len(self.receiverBuffer) == 0:
                return None

            data = min(self.receiverBuffer)

            if "data" in data[1] and data[0] == self.nextSequenceAppLock:
                print("packet to application: ", self.nextSequenceAppLock)
                with self.sequenceAppLock:
                    self.nextSequenceAppLock += 1
                # removing header information before forwarding data to application
                self.receiverBuffer.remove(data)
                return data[1]["data"]
            else:
                return None
        except Exception as e:
            print("Error occured in reliable read: ", e)

    def writeHelper(self, data, data_type, retransmit=False):
        try:
            if self.sock == None:
                raise createSocketError("Socket not created")

            data = deepcopy(data)
            # setting type of packet in header information
            data["type"] = data_type
            if data_type == "DATA" and retransmit == False:
                with self.senderLock:
                    self.senderBuffer.append((data["seq"], data, time.time()))

            data_send = pickle.dumps(data)

            if len(data_send) > RUDP.packetSize:
                raise Exception("Packet size greater the allowed size.")

            rn = random.randint(0, 11)

            # simulating ACK packet loss
            if rn >= RUDP.packetLosses:
                try:
                    with self.sendSocketLock:
                        self.sock.sendall(data_send)
                except Exception as _:
                    return
            else:
                print("packet lost")
        except Exception as e:
            print("Error occured in reliable write", e)

    def sendNonBlockingMode(self, data):
        try:
            if len(self.senderBuffer) > RUDP.windowSize:
                print("buffer size full")
                return False
            data = deepcopy(data)  # if user modify the object, the shouldn't be changed
            seq = self.getNextSequenceNumber()
            data_snd = {}  # it will store header information
            data_snd["seq"] = seq
            data_snd["data"] = data
            data_snd["hash"] = hashlib.md5(pickle.dumps(data)).hexdigest()
            self.writeHelper(data_snd, "DATA")
            return True
        except Exception as e:
            print("Error in non-blocking send: ", e)

    def getNextSequenceNumber(self):
        try:
            with self.sequenceLock:
                self.sequenceNumber += 1
                return self.sequenceNumber
        except Exception as e:
            print("Failed to retrieve next sequence Number: ", e)

    def getBufferSize(self):
        try:
            return self.receiverBuffer
        except Exception as e:
            print("Error in getting buffer size", e)

    @staticmethod
    def printReliableStats():
        print("bufferSize (bytes recv function accepts): ", RUDP.bufferSize)
        print("windowSize (number of packets in send or recv buffer): ", RUDP.windowSize)
        print("packetSize (Max size of send packet in bytes): ", RUDP.packetSize)
        print("connectionTimeout (time in seconds to retransmit packet): ", RUDP.connectionTimeout)
        print("blockAndSleep (time in seconds to recheck buffer): ", RUDP.blockAndSleep)
