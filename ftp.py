import os, sys, time, random
from tqdm import tqdm
from RUDP_protocol import RUDP


port1 = 8083
port2 = 8084
BUFFERSIZE = 512


def appendFiles(filename):
    Files = []
    for file in os.listdir("storage/" + filename):
        if os.path.isfile("storage/" + file):
            Files.append(file)
    return Files


def retrieveFilesHelper(filename):
    if os.path.isfile("storage/" + filename):
        return [filename]
    elif os.path.isdir("storage/" + filename):
        FilesList = appendFiles(filename)
        return FilesList
    else:
        print("File/Folder not found")
        return []


def fileDetails(file):
    file_path = "storage/" + file
    f = open(file_path, "rb")
    filesize = os.path.getsize(file_path)
    print(f"sending {file} to client")
    return f, filesize

def sendToSock(data, socket, indicator, sendData, filesize):
    socket.send(data)
    update_value = min(BUFFERSIZE, filesize - sendData)
    sendData += BUFFERSIZE
    indicator.update(update_value)
    return sendData


def serverLoop(socket, file_list):
    for file in file_list:
        try:
            f, filesize = fileDetails(file)
            data = (file, filesize)
            socket.send(data)
            print(f"filesize: {filesize}")

            sendData = 0
            try: 
                with tqdm(total = filesize) as indicator:
                    data = f.read(BUFFERSIZE)
                    while data:
                        sendData = sendToSock(data, socket, indicator, sendData, filesize)
                        data = f.read(BUFFERSIZE)
                print("\ndone sending")
            except Exception as e:
                print(e)
            finally:
                f.close()  
        except Exception as e:
            print(e)

def receiveFromSock(socket, receivedData, indicator, fileName):
    data = socket.recv()
    receivedData += len(data)
    fileName.write(data)
    indicator.update(len(data))
    return receivedData

def clientLoop(socket):
    try:
        while True:
            print("\nwaiting for another file...")
            filename, filesize = socket.recv()
            print(f"filename: {filename}, filesize: {filesize}")
            receivedData = 0
            path = "storage/received_files/"
            try:
                with open(path + filename, "wb+") as f:
                    with tqdm(total=filesize) as indicator:
                        while True:
                            receivedData = receiveFromSock(socket, receivedData, indicator, f)
                            if filesize <= receivedData:
                                break
                    print("\ntransfer complete")
            except Exception as e:
                print(e)
            finally:
                f.close()
    except Exception as e:
        print(e)


def server():
    socket = RUDP("localhost", port1)
    socket.connect("localhost", port2)
    socket.listen()
    try:
        while True:
            filename = input("\nfile or folder name (in storage folder): ")
            if not filename:
                filename = "L.txt"
            time.sleep(5)
            file_list = retrieveFilesHelper(filename)
            print(f"sending {len(file_list)} files to client.")
            serverLoop(socket, file_list)
    except Exception as e:
        print(e)

def client():
    socket = RUDP("localhost", port2)
    socket.connect("localhost", port1)
    socket.listen()
    time.sleep(5)
    clientLoop(socket)


if __name__ == "__main__":
    while True:
        t = input("Enter 'server' or 'client': ")
        if t == "server":
            server()
            break
        elif t == "client":
            client()
            break
        else:
            print("wrong input, Enter 'client' or 'server'")
