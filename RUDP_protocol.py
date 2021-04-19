import builtins, hashlib, pickle, random, socket, time
from collections.abc import Hashable
from copy import deepcopy
from pprint import pprint
from threading import Lock, Thread

# change it to false for stdout prints from protocol
DEBUG_MODE = 0


class createSocketError(RuntimeError):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class createConnectionError(RuntimeError):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def switch(self, val, *args, **kargs):
    if val == 1:
        builtins.print(*args, **kargs)


def print(self, *args, **kargs):
    if DEBUG_MODE == 1:
        switch(1, args, kargs)


""" RELIABKE UDP PROTOCOL  """


class RUDP:
    # consntants for the protocol
    # in bytes
    bufferSize = 1500
    packetSize = 1400

    # size of buffer windows
    windowSize = 1000

    # in seconds: starting of retransmission thread
    connectionTimeout = 1

    # in range(0, 11), 0 for no loss
    packetLosses = 0
    blockAndSleep = 0.00001

    """
    Helper functions to Initialize buffer, sequence Numbers, sockets etc. 
    """

    def seqLock(self):
        self.sequenceLock = Lock()
        self.sequenceAppLock = Lock()
        # last seq number of packet transferred to application
        self.nextSequenceAppLock = self.sequenceNumber + 1

    def packet_loss_rate(self, value):
        if 10 >= value and value >= 0:
            RUDP.PACKET_LOSS = value
        else:
            raise Exception("Value not in range. (0 - 10)")

    def initializeSendRecvLock(self):
        self.senderLock = Lock()
        self.recieveSocketLock = Lock()
        self.sendSocketLock = Lock()

    def initializeConn(self):
        self.closeConnTime = 0
        self.statusOfConn = False

    def initializeSeq(self):
        self.sequenceNumber = 0
        self.sequenceHash = {}

    def createSock(self, interface, port):
        self.interface = interface
        self.port = port
        self.sock = self.socketInit(interface, port)

    def initializeBuffer(self):
        self.receiverBuffer = []
        self.senderBuffer = []

    def __init__(self, interface, port):
        self.createSock(interface, port)
        self.initializeBuffer()
        self.initializeSeq()
        self.initializeConn()
        self.initializeSendRecvLock()
        self.seqLock()

    """
    Standard socket functions for creating socket and sending/recieving data 
    with reliability helper functions called for reliable UDP transfer protocol
    """

    def socketInit(self, interface, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
            if not self.statusOfConn:
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
                if not self.statusOfConn and len(self.senderBuffer) == 0:
                    return
                with self.senderLock:
                    print(
                        "The lock has been acquired by the retransmiting thread to retransmit  timed out packets"
                    )
                    currentSenderBuffer = self.senderBuffer
                    i = 0
                    while i < len(currentSenderBuffer):
                        time_now = time.time()
                        diff = time_now - currentSenderBuffer[i][2]
                        if RUDP.connectionTimeout <= diff:
                            print("Retransmitting: ", currentSenderBuffer[i][0])
                            self.writeHelper(
                                currentSenderBuffer[i][1], "DATA", retransmit=True
                            )
                        else:
                            # The remaining packets have not been timed out yet
                            break
                        i += 1
        except Exception as e:
            print("Error occured while retransmiting packets: ", e)
        finally:
            print("Number of packets in the sender buffer: ", len(currentSenderBuffer))

    def listenerHelper(self):
        try:
            if self.sock == None:
                raise createSocketError("Socket not created")

            # counts number of acke'd packets still in sent list
            count_ACK = 0
            map_ACK = set()
            print("Listening at {}:".format(self.sock.getsockname()))

            while True:
                try:
                    with self.recieveSocketLock:
                        data, address = self.sock.recvfrom(RUDP.bufferSize)
                        print("Connected to client at {}".format(address))
                        receivedData = pickle.loads(data)
                        print(receivedData)
                except Exception as e:
                    print(e)

                # cases for received packet to be an ACK
                if receivedData["type"] == "ACK":
                    print("Received ACK for: ", receivedData["seqence_ACK"])
                    print("Number of packets in buffer: ", len(self.senderBuffer))
                    count_ACK += 1
                    map_ACK.add(receivedData["seqence_ACK"])
                    partition = RUDP.windowSize / 10
                    diff = time.time() - self.closeConnTime

                    if count_ACK >= partition or (
                        diff >= 5 * RUDP.connectionTimeout and not self.statusOfConn
                    ):
                        count_ACK = 0
                        tempList = []
                        with self.senderLock:
                            print("Lock is acquired by the Listening Thread....")
                            currentBuffer = self.senderBuffer
                            i = 0
                            while i < len(currentBuffer):
                                if currentBuffer[i][0] not in map_ACK:
                                    tempList.append(currentBuffer[i])
                                i += 1
                            self.senderBuffer = tempList
                            map_ACK = set()
                else:
                    partition = RUDP.windowSize / 10
                    diff = RUDP.windowSize - partition
                    if receivedData["seq"] >= (self.nextSequenceAppLock + diff):
                        # the recieved data is outside 90% of the buffer window size
                        continue

                    data = receivedData["data"]

                    if (
                        hashlib.md5(pickle.dumps(data)).hexdigest()
                        != receivedData["hash"]
                    ):
                        # check if any inconsistant data has arrived
                        print("inconsistent data received")
                        continue

                    if (
                        len(self.receiverBuffer) < RUDP.windowSize
                    ) or self.sequenceHash.get(receivedData["seq"]) != None:
                        print("sending ACK for: ", receivedData["seq"])
                        sendData = {}
                        sendData["seqence_ACK"] = receivedData["seq"]
                        self.writeHelper(sendData, "ACK")

                    if (
                        len(self.receiverBuffer) < RUDP.windowSize
                        and self.sequenceHash.get(receivedData["seq"]) == None
                    ):
                        self.receiverBuffer.append((receivedData["seq"], receivedData))
                        self.sequenceHash[receivedData["seq"]] = True
                    else:
                        print("data rejected: data already recieved or buffer full")
        except Exception as e:
            print("Error occured in reliable listener: ", e)

    def readHelper(self):
        try:
            if len(self.receiverBuffer) == 0:
                return None
            data = self.receiverBuffer[0]
            for val in self.receiverBuffer:
                data = min(data, val)
            if "data" in data[1] and data[0] == self.nextSequenceAppLock:
                with self.sequenceAppLock:
                    self.nextSequenceAppLock += 1
                # Remove header data before forwading
                self.receiverBuffer.remove(data)
                return data[1]["data"]
            else:
                return None
        except Exception as e:
            print("Error occured in reliable read: ", e)

    def writeHelper(self, data, typeData, retransmit=False):
        try:
            if self.sock == None:
                raise createSocketError("Socket not created")
            data = deepcopy(data)
            # setting type of packet in header information
            data["type"] = typeData
            if typeData == "DATA" and retransmit == False:
                with self.senderLock:
                    item = (data["seq"], data, time.time())
                    self.senderBuffer.append(item)
            sendData = pickle.dumps(data)
            if RUDP.packetSize < len(sendData):
                raise Exception("Packet size greater the allowed size.")
            rn = random.randint(0, 11)
            # simulating ACK packet loss
            if rn >= RUDP.packetLosses:
                try:
                    with self.sendSocketLock:
                        self.sock.sendall(sendData)
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
            # if user modify the object, the shouldn't be changed
            data = deepcopy(data)
            self.sequenceNumber += 1
            seq = self.sequenceNumber
            # it will store header information
            sendData = {}
            sendData["seq"] = seq
            sendData["data"] = data
            sendData["hash"] = hashlib.md5(pickle.dumps(data)).hexdigest()
            self.writeHelper(sendData, "DATA")
            return True
        except Exception as e:
            print("Error in non-blocking send: ", e)

    @staticmethod
    def printReliableStats():
        print("bufferSize (bytes recv function accepts): ", RUDP.bufferSize)
        print(
            "windowSize (number of packets in send or recv buffer): ", RUDP.windowSize
        )
        print("packetSize (Max size of send packet in bytes): ", RUDP.packetSize)
        print(
            "connectionTimeout (time in seconds to retransmit packet): ",
            RUDP.connectionTimeout,
        )
        print("blockAndSleep (time in seconds to recheck buffer): ", RUDP.blockAndSleep)
