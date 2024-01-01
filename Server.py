'''
    ##  Implementation of registry
    ##  150114822 - Eren Ulaş
'''
import asyncio
import socket
import threading
import select
import logging
import db
import bcrypt
import pickle


# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port
        # socket of the peer
        self.tcpClientSocket = tcpClientSocket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        print("New thread started for " + ip + ":" + str(port))

 # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print("Connection from: " + self.ip + ":" + str(port))
        print("IP Connected: " + self.ip)

        while True:
            try:
                # waits for incoming messages from peers
                message = self.tcpClientSocket.recv(1024).decode().split()
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message))
                #   JOIN    #
                if message[0] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message[1]):
                        response = "join-exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # join-success is sent to peer,
                    # if an account with this username is not exist, and the account is created
                    else:
                        db.register(message[1], message[2])
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                #   LOGIN    #
                elif message[0] == 'LOGIN':
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message[1]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message[1]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrieved_hashed_pass = db.get_password(message[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if bcrypt.checkpw(message[2].encode('utf-8'), retrieved_hashed_pass.encode('utf-8')):
                            self.username = message[1]
                            with self.lock:  # Acquire the lock before modifying shared data
                                try:
                                    tcpThreads[self.username] = self
                                finally:
                                    pass  # The lock is automatically released when the 'with' block is exited
                            db.user_login(message[1], self.ip, message[3])
                            # login-success is sent to peer,
                            # and a udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            onlinePeers.append(self.username)
                            self.tcpClientSocket.send(response.encode())
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                #   LOGOUT  #
                elif message[0] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this
                    # user is cancelled
                    if len(message) > 1 and message[1] is not None and db.is_account_online(message[1]):
                        db.user_logout(message[1])
                        self.lock.acquire()
                        try:
                            if message[1] in tcpThreads:
                                del tcpThreads[message[1]]
                        finally:
                            self.lock.release()
                        print(self.ip + ":" + str(self.port) + " is logged out")
                        onlinePeers.remove(self.username)
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        break

                elif message[0] == "PRINT":
                    response = "List of online users: " + ', '.join(str(user) for user in onlinePeers)
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    self.tcpClientSocket.send(response.encode())

                elif message[0] == "PRINT_CHATROOMS":
                    response_db = db.get_all_chatroom_names()
                    if "NO CHATROOMS HAVE BEEN CREATED YET" not in response_db:
                        # response = "List of chat rooms:\n" + '\n'.join(str(room_name) for room_name in response_db)
                        response = "List of chat rooms: " + ' '.join(response_db)
                        logging.info(
                            "Send to " + self.ip + ":" + str(self.port) + " -> " + "NO CHATROOMS HAVE BEEN CREATED YET")
                        self.tcpClientSocket.send(response.encode())
                    else:
                        self.tcpClientSocket.send(response_db.encode())

                elif message[0] == "CREATE":
                    async def create_chatroom():
                        response_db = await db.save_chatroom(message[1])
                        logging.info("Send to " + str(self.ip) + ":" + str(self.port) + " -> " + response_db)
                        self.tcpClientSocket.send(response_db.encode())

                        # Call the coroutine using the thread's event loop
                    self.loop.run_until_complete(create_chatroom())

                elif message[0] == "JOIN-ROOM":
                    async def add_db():
                        # your asynchronous code here
                        await db.add_member(message[1], message[2], message[3], message[4], message[5])

                    exists, response_db = db.is_room_exits(message[1])
                    if not exists:
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response_db)
                        self.tcpClientSocket.send(response_db.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    # elif db.is_member_inroom(message[1], message[2])[0]:
                    #     response = "Member already in room.."
                    #     logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    #     self.tcpClientSocket.send(response.encode())
                    else:
                        response = "MEMBER-JOINED" + " " + message[2] + " " + message[3] + " " + message[5]
                        members_list = db.get_chatroom_members(message[1])
                        # Convert members_list to a byte-like object
                        # if ("not found" not in members_list):
                        #     members_list_bytes = pickle.dumps(members_list)
                        #     for member in members_list:
                        #         member_name = member["username"]
                        #         if member_name in tcpThreads:
                        #             if member_name != self.username:
                        #                 tcpThreads[member_name].tcpClientSocket.send(response.encode())
                        #         else:
                        #             print(f"Key '{member_name}' not found in tcpThreads.")
                        if ("not found" not in members_list):
                            members_list_bytes = pickle.dumps(members_list)
                            # Acquire lock before iterating through tcpThreads
                            with lock:
                                for member in members_list:
                                    member_name = member["username"]
                                    if member_name in tcpThreads:
                                        if member_name != self.username:
                                            tcpThreads[member_name].tcpClientSocket.send(response.encode())
                                    else:
                                        print(f"Key '{member_name}' not found in tcpThreads.")
                            # send to the new member the list of members too !
                            # response = "You joined the room , start chatting !"
                            # self.tcpClientSocket.send(response.encode())
                            self.tcpClientSocket.sendall(members_list_bytes)
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            #db.add_member(message[1], message[2], message[3], message[4], message[5])
                            self.loop.run_until_complete(add_db())
                        else:
                            response = "You are the first member to join the room ! "
                            #db.add_member(message[1], message[2], message[3], message[4], message[5])
                            self.loop.run_until_complete(add_db())
                            self.tcpClientSocket.send(response.encode())
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    self.loop.close()



                elif message[0] == "LEAVE":
                    response_peers = "Peer-LEFT" + message[1] + " " + message[2] #message[1]=username, message[2]=room_name
                    response_peerleft = "YOU LEFT THE ROOM"
                    # for member in members_list:
                    #     member_name = member["username"]
                    #     if member_name != self.username:
                    #         if member_name in tcpThreads:
                    #             tcpThreads[member_name].tcpClientSocket.send(response_peers.encode())
                    #         logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response_peerleft)
                    # Acquire lock before iterating over members_list
                    with lock:
                        for member in members_list:
                            member_name = member["username"]
                            if member_name != self.username:
                                if member_name in tcpThreads:
                                    tcpThreads[member_name].tcpClientSocket.send(response_peers.encode())
                                logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response_peerleft)
                        self.tcpClientSocket.send(response_peerleft.encode())
                        response_db = db.leave_room(message[1], message[2])

                #   SEARCH  #
                elif message[0] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message[1]):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message[1]):
                            peer_info = db.get_peer_ip_port(message[1])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                elif message[0] == "PORTNUMBER":
                   # Acquire the lock before accessing shared data
                    with self.lock:
                        if self.username in udpPortnumbers:
                            udp_port = udpPortnumbers[self.username]
                            self.tcpClientSocket.send(str(udp_port).encode())
                        else:
                            print(f"Username '{self.username}' not found in udpPortnumbers")

            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))

    # function for resetting the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()



# implementation of the udp server thread for clients
class UDPServer(threading.Thread):

    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(80, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket
        # Define a lock for thread safety
        self.lock = threading.Lock()


    # if hello message is not received before timeout
    # then peer is disconnected
    # def waitHelloMessage(self):
    #     if self.username is not None:
    #         db.user_logout(self.username)
    #         if self.username in tcpThreads:
    #             del tcpThreads[self.username]
    #             del udpPortnumbers[self.username]
    #             onlinePeers.remove(self.username)
    #             member_inroom, room_name = db.is_member_inroom(self.username)
    #             if room_name is not None:
    #                 db.remove_member(self.username, room_name)
    #                 print(f'Removed {self.username} from chatroom: {room_name}')
    #                 # Check if the chatroom exists before trying to get members
    #                 is_room_exists, room_status = db.is_room_exits(room_name)
    #                 if is_room_exists:
    #                     members_list = db.get_chatroom_members(room_name)
    #                     for member in members_list:
    #                         member_name = member["username"]
    #                         if member_name in tcpThreads:
    #                             if member_name != self.username:
    #                                 response = f'{self.username} left the room due to disconnection'
    #                                 tcpThreads[member_name].tcpClientSocket.send(response.encode())
    #                 else:
    #                     print(f"Chatroom '{room_name}' does not exist.")

    def waitHelloMessage(self):
        if self.username is not None:
            with self.lock:  # Acquire the lock before accessing shared data
                db.user_logout(self.username)
                if self.username in tcpThreads:
                    del tcpThreads[self.username]
                    del udpPortnumbers[self.username]
                    onlinePeers.remove(self.username)
                    member_inroom, room_name = db.is_member_inroom(self.username)
                    if room_name is not None:
                        print(f'Removed {self.username} from chatroom: {room_name}')
                        # Check if the chatroom exists before trying to get members
                        is_room_exists, room_status = db.is_room_exits(room_name)
                        if is_room_exists:
                            members_list = db.get_chatroom_members(room_name)
                            for member in members_list:
                                member_name = member["username"]
                                if member_name in tcpThreads:
                                    if member_name != self.username:
                                        response = f'{self.username} left the room due to disconnection'
                                        tcpThreads[member_name].tcpClientSocket.send(response.encode())
                            db.remove_member(self.username, room_name)
                        else:
                            print(f"Chatroom '{room_name}' does not exist.")
            self.tcpClientSocket.close()
            print("Removed " + self.username + " from online peers")
        else:
            print("Error: username or udpServer is not properly initialized.")

    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(30, self.waitHelloMessage)
        self.timer.start()


# tcp and udp server port initializations
print("\033[31mRegisty started...\033[0m")
port = 15600
portUDP = 15500

# db initialization
db = db.DB()

# gets the ip address of this peer
# first checks to get it for windows devices
# if the device that runs this application is not windows
# it checks to get it for macos devices
hostname = socket.gethostname()
try:
    host = socket.gethostbyname(hostname)
except socket.gaierror:
    import netifaces as ni

    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

print("\033[96mRegistry IP address:\033[0m " + host)
print("\033[96mRegistry port number: \033[0m" + str(port))

chatrooms = []
# onlinePeers list for online account
onlinePeers = []
# accounts list for accounts
accounts = []
# tcpThreads list for online client's thread
tcpThreads = {}
# udp port number of each peer
udpPortnumbers = {}

# tcp and udp socket initializations
tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tcpSocket.bind((host, port))
udpSocket.bind((host, portUDP))
tcpSocket.listen(5)
db.delete_all_online_peers()

# input sockets that are listened
inputs = [tcpSocket, udpSocket]

# lock
lock=threading.Lock()

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO)

# as long as at least a socket exists to listen registry runs
while inputs:

    print("\033[92mListening for incoming connections...\033[0m")
    # monitors for the incoming connections
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        # if the message received comes to the tcp socket
        # the connection is accepted and a thread is created for it, and that thread is started
        if s is tcpSocket:
            tcpClientSocket, addr = tcpSocket.accept()
            newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
            newThread.start()
        # if the message received comes to the udp socket
        elif s is udpSocket:
            # received the incoming udp message and parses it
            message, clientAddress = s.recvfrom(1024)
            message = message.decode().split()
            print("UDP PORT IS:", clientAddress[1], "PORT NUMBER IS:", clientAddress[0])
            # checks if it is a hello message
            # if message[0] == "HELLO":
            #     # checks if the account that this hello message
            #     # is sent from is online
            #     if message[1] in tcpThreads:
            #         # resets the timeout for that peer since the hello message is received
            #         tcpThreads[message[1]].resetTimeout()
            #         print("Hello is received from " + message[1])
            #         logging.info(
            #             "Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))
            #         # sending to the client its udp port which he sent from the message for future usage
            #         # Check if the username is already in udpPortnumbers
            #         if message[1] not in udpPortnumbers:
            #             udpPortnumbers[message[1]] = int(clientAddress[1])

            # checks if it is a hello message
            if message[0] == "HELLO":
                with lock:  # Acquire the lock before accessing shared data
                    # checks if the account that this hello message is sent from is online
                    if message[1] in tcpThreads:
                        print("Hello is received from " + message[1])
                        logging.info(
                            "Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(
                                message))
                        # sending to the client its udp port which he sent from the message for future usage
                        # Check if the username is already in udpPortnumbers
                        if message[1] not in udpPortnumbers:
                            udpPortnumbers[message[1]] = int(clientAddress[1])
                        # resets the timeout for that peer since the hello message is received
                        tcpThreads[message[1]].resetTimeout()


# registry tcp socket is closed
tcpSocket.close()
udpSocket.close()
