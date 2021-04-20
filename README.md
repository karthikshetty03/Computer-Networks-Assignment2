## CS F303 Computer Networks Assignment 2
## Reliable UDP (RUDP)


### Shetty Karthik Ravindra 2018A7PS0141H
### Akshat Bajpai 2018A7PS0498H
### Koustubh Sharma 2018A7PS0114H
### Rishabh Baid 2018A7PS0189H
### Abhirath Singh Parmar 2018A7PS0521H
### Aryan Sharma 2018A7PS0245H


RUDP provides reliable communication over unreliable UDP protocol and also directly works with
python objects for simplicity. This class provides API ​ ( application program interface) for the
underlying reliable application layer protocol. An object of this class should be instantiated to set
up communication with a peer. This protocol requires python3 to run and doesn’t have any other
dependency. All standard python packages are used to build this protocol.

the actual protocol RUDP doesn't have any dependency other than python3.
but the file transfer uses "tqdm" library to display progress bar.

### 1) File Transfer

	setup:
		$ pip3 install pipenv
		$ pipenv install

		terminal 1:
			$ pipenv shell
			$ python3 file-transfer.py
			$ client

		terminal 2:
			$ pipenv shell
			$ python3 file-transfer.py
			$ server

#### description:
Now, server will ask for a path, the path can be a file or a folder,
if it's a file it will be transfered and if it's a folder, all the files
in it's root location will be transferred sequentially. Server will look for
files inside the./storage folder only. (you can leave the path blank to transfer
the default file i.e. 'assignment-3.pdf')

All the files received by the client are stored inside ./storage/received_files

	NOTE: Client should be started first in all the cases.


### 2) Performance measurement

to measure the bandwidth of the protocol, you have to run performance_measurement.py in two different
terminals, first start the client (receiver) by inputing '2' then start the server (sender) by inputing
'1'. This script will run for 1 minute and then output the bandwidth and bytes sent.

#### setup:

	in terminal 1
		$ python3 performance_test.py
		$ 2

	in terminal 2
		$ python3 performance_test.py
		$ 1

### 3) Reliability test

to test reliability, just run reliablity_test.py in both the terminals and server will send 100 packets in sequence
and client which check if all 100 packets reached and are in order.


#### setup:

	in terminal 1
		$ python3 reliability_test.py
		$ 2

	in terminal 2
		$ python3 reliability_test.py
		$ 1
