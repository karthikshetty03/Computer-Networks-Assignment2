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
        self.sequenceAppLock = Lock()
        self.sequenceLock = Lock()
        # last seq number of packet transferred to application
        self.nextSequenceAppLock = self.sequenceNumber
        self.nextSequenceAppLock += 1

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
        self.port = port
        self.interface = interface
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
            item = (interface, port)
            sock.bind(item)
            return sock
        except Exception as e:
            print("Eroor occurself.nextSequenceAppLocked while creating socket!: ", e)

    def connect(self, interface, port):
        try:
            item = (interface, port)
            self.sock.connect(item)
            self.statusOfConn = True
        except Exception as e:
            print("Error occured while trying to connect: ", e)

    def listen(self):
        try:
            if not self.statusOfConn:
                raise createConnectionError("First connect to other peer.")

            # create listener and retransmission threads
            listenerThread = Thread(target=self.listenerHelper)
            retransmissionThread = Thread(target=self.retransmitHelper)

            # start listener and retransmission threads
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
            if not blocking:
                data = self.readHelper()
                data = deepcopy(data)
                return data
            else:
                while True:
                    data = self.readHelper()
                    if data != None:
                        data = deepcopy(data)
                        return data
                    time.sleep(RUDP.blockAndSleep)

        except Exception as e:
            print("Error occured while receiving data: ", e)

    def close(self):
        try:
            self.statusOfConn = False
            currTime = time.time()
            self.closeConnTime = currTime
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
                    try:
                        print("Lock acquired by retransmiting thread")
                        currSB = self.senderBuffer
                        i = 0
                        while i < len(currSB):
                            time_now = time.time()
                            diff = time_now - currSB[i][2]
                            if RUDP.connectionTimeout <= diff:
                                print("Retransmitting: ", currSB[i][0])
                                self.writeHelper(currSB[i][1], "DATA", retransmit=True)
                            else:
                                # The remaining packets have not been timed out yet
                                break
                            i += 1
                    except Exception as e:
                        print(e)
        except Exception as e:
            print("Error occured while retransmiting packets: ", e)
        finally:
            print("Number of packets in the sender buffer: ", len(currSB))

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
                    myval = 5 * RUDP.connectionTimeout
                    cs = self.statusOfConn
                    if count_ACK >= partition or (diff >= myval and not cs):
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
                    myhash = hashlib.md5(pickle.dumps(data)).hexdigest()
                    if myhash != receivedData["hash"]:
                        # check if any inconsistant data has arrived
                        print("inconsistent data received")
                        continue

                    cl = len(self.receiverBuffer)
                    myobj = self.sequenceHash.get(receivedData["seq"])
                    if (cl < RUDP.windowSize) or myobj != None:
                        print("sending ACK for: ", receivedData["seq"])
                        sendData = {}
                        sendData["seqence_ACK"] = receivedData["seq"]
                        self.writeHelper(sendData, "ACK")

                    cl = len(self.receiverBuffer)
                    myobj = self.sequenceHash.get(receivedData["seq"])
                    if cl < RUDP.windowSize and myobj == None:
                        self.receiverBuffer.append((receivedData["seq"], receivedData))
                        self.sequenceHash[receivedData["seq"]] = True
                    else:
                        print("data rejected:  buffer full or data already recieved!")
        except Exception as e:
            print("Error occured in reliable listener: ", e)

    def readHelper(self):
        try:
            cl = len(self.receiverBuffer)
            if cl == 0:
                return None
            data = self.receiverBuffer[0]
            for val in self.receiverBuffer:
                data = min(data, val)
            if "data" in data[1] and data[0] == self.nextSequenceAppLock:
                with self.sequenceAppLock:
                    try:
                        self.nextSequenceAppLock += 1
                    except Exception as e:
                        print(e)
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
            if typeData == "DATA" and not retransmit:
                with self.senderLock:
                    try:
                        currTime = time.time()
                        item = (data["seq"], data, currTime)
                        self.senderBuffer.append(item)
                    except Exception as e:
                        print(e)
            sendData = pickle.dumps(data)
            if RUDP.packetSize < len(sendData):
                raise Exception("Packet size exceeds max allowed size....")
            rn = random.randint(0, 11)
            # simulating ACK packet loss
            if rn >= RUDP.packetLosses:
                try:
                    with self.sendSocketLock:
                        self.sock.sendall(sendData)
                except Exception as e:
                    print(e)
                    return
            else:
                print("Packet has been lost....")
        except Exception as e:
            print("Error occured in reliable write", e)

    def getData(self, seq, data):
        keys = ["data", "seq", "hash"]
        values = [data, seq, hashlib.md5(pickle.dumps(data)).hexdigest()]
        sendData = {k: v for k, v in zip(keys, values)}
        return sendData

    def sendNonBlockingMode(self, data):
        try:
            if len(self.senderBuffer) > RUDP.windowSize:
                print("buffer size is full")
                return False
            # if user modify the object, the shouldn't be changed
            data = deepcopy(data)
            self.sequenceNumber += 1
            seq = self.sequenceNumber
            # it will store header information
            sendData = self.getData(seq, data)
            self.writeHelper(sendData, "DATA")
            return True
        except Exception as e:
            print("Error in non-blocking send: ", e)
