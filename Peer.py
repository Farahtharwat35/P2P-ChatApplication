'''
    ##  Implementation of peer
    ##  Each peer has a client and a server side that runs on different threads
    ##  150114822 - Eren Ulaş
'''

import socket
import threading
import os
import select
import logging
import bcrypt



# Server side of peer
class PeerServer(threading.Thread):

    # Peer server initialization
    def __init__(self, username, peerServerPort):
        threading.Thread.__init__(self)
        # keeps the username of the peer
        self.username = username
        # tcp socket for peer server
        self.tcpServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # port number of the peer server
        self.peerServerPort = peerServerPort
        # if 1, then user is already chatting with someone
        # if 0, then user is not chatting with anyone
        self.isChatRequested = 0
        # keeps the socket for the peer that is connected to this peer
        self.connectedPeerSocket = None
        # keeps the ip of the peer that is connected to this peer's server
        self.connectedPeerIP = None
        # keeps the port number of the peer that is connected to this peer's server
        self.connectedPeerPort = None
        # online status of the peer
        self.isOnline = True
        # keeps the username of the peer that this peer is chatting with
        self.chattingClientName = None

    # main method of the peer server thread
    def run(self):

        print("Peer server started...")

        # gets the ip address of this peer
        # first checks to get it for windows devices
        # if the device that runs this application is not windows
        # it checks to get it for macos devices
        hostname = socket.gethostname()
        try:
            self.peerServerHostname = socket.gethostbyname(hostname)
        except socket.gaierror:
            import netifaces as ni
            self.peerServerHostname = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

        # ip address of this peer
        # self.peerServerHostname = 'localhost'
        # socket initializations for the server of the peer
        self.tcpServerSocket.bind((self.peerServerHostname, self.peerServerPort))
        self.tcpServerSocket.listen(4)
        # inputs sockets that should be listened
        inputs = [self.tcpServerSocket]
        # server listens as long as there is a socket to listen in the inputs list and the user is online
        while inputs and self.isOnline:
            # monitors for the incoming connections
            try:
                readable, writable, exceptional = select.select(inputs, [], [])
                # If a server waits to be connected enters here
                for s in readable:
                    # if the socket that is receiving the connection is 
                    # the tcp socket of the peer's server, enters here
                    if s is self.tcpServerSocket:
                        # accepts the connection, and adds its connection socket to the inputs list
                        # so that we can monitor that socket as well
                        connected, addr = s.accept()
                        connected.setblocking(0)
                        inputs.append(connected)
                        # if the user is not chatting, then the ip and the socket of
                        # this peer is assigned to server variables
                        if self.isChatRequested == 0:
                            print(self.username + " is connected from " + str(addr))
                            self.connectedPeerSocket = connected
                            self.connectedPeerIP = addr[0]
                    # if the socket that receives the data is the one that
                    # is used to communicate with a connected peer, then enters here
                    else:
                        # message is received from connected peer
                        messageReceived = s.recv(1024).decode()
                        # logs the received message
                        logging.info("Received from " + str(self.connectedPeerIP) + " -> " + str(messageReceived))
                        # if message is a request message it means that this is the receiver side peer server
                        # so evaluate the chat request
                        if len(messageReceived) > 11 and messageReceived[:12] == "CHAT-REQUEST":
                            # text for proper input choices is printed however OK or REJECT is taken as input in main process of the peer
                            # if the socket that we received the data belongs to the peer that we are chatting with,
                            # enters here
                            if s is self.connectedPeerSocket:
                                # parses the message
                                messageReceived = messageReceived.split()
                                # gets the port of the peer that sends the chat request message
                                self.connectedPeerPort = int(messageReceived[1])
                                # gets the username of the peer sends the chat request message
                                self.chattingClientName = messageReceived[2]
                                # prints prompt for the incoming chat request
                                print("Incoming chat request from " + self.chattingClientName + " >> ")
                                print("Enter OK to accept or REJECT to reject:  ")
                                # makes isChatRequested = 1 which means that peer is chatting with someone
                                self.isChatRequested = 1
                            # if the socket that we received the data does not belong to the peer that we are chatting with
                            # and if the user is already chatting with someone else(isChatRequested = 1), then enters here
                            elif s is not self.connectedPeerSocket and self.isChatRequested == 1:
                                # sends a busy message to the peer that sends a chat request when this peer is 
                                # already chatting with someone else
                                message = "BUSY"
                                s.send(message.encode())
                                # remove the peer from the inputs list so that it will not monitor this socket
                                inputs.remove(s)
                        # if an OK message is received then ischatrequested is made 1 and then next messages will be shown to the peer of this server
                        elif messageReceived == "OK":
                            self.isChatRequested = 1
                        # if an REJECT message is received then ischatrequested is made 0 so that it can receive any other chat requests
                        elif messageReceived == "REJECT":
                            self.isChatRequested = 0
                            inputs.remove(s)
                        # if a message is received, and if this is not a quit message ':q' and 
                        # if it is not an empty message, show this message to the user
                        elif messageReceived[:2] != ":q" and len(messageReceived) != 0:
                            print(self.chattingClientName + ": " + messageReceived)
                        # if the message received is a quit message ':q',
                        # makes ischatrequested 1 to receive new incoming request messages
                        # removes the socket of the connected peer from the inputs list
                        elif messageReceived[:2] == ":q":
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            # connected peer ended the chat
                            if len(messageReceived) == 2:
                                print("User you're chatting with ended the chat")
                                print("Press enter to quit the chat: ")
                        # if the message is an empty one, then it means that the
                        # connected user suddenly ended the chat(an error occurred)
                        elif len(messageReceived) == 0:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            print("User you're chatting with suddenly ended the chat")
                            print("Press enter to quit the chat: ")
            # handles the exceptions, and logs them
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
            except ValueError as vErr:
                logging.error("ValueError: {0}".format(vErr))


# Client side of peer
class PeerClient(threading.Thread):
    # variable initializations for the client side of the peer
    def __init__(self, ipToConnect, portToConnect, username, peerServer, responseReceived):
        threading.Thread.__init__(self)
        # keeps the ip address of the peer that this will connect
        self.ipToConnect = ipToConnect
        # keeps the username of the peer
        self.username = username
        # keeps the port number that this client should connect
        self.portToConnect = portToConnect
        # client side tcp socket initialization
        self.tcpClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # keeps the server of this client
        self.peerServer = peerServer
        # keeps the phrase that is used when creating the client
        # if the client is created with a phrase, it means this one received the request
        # this phrase should be none if this is the client of the requester peer
        self.responseReceived = responseReceived
        # keeps if this client is ending the chat or not
        self.isEndingChat = False

    # main method of the peer client thread
    def run(self):
        print("Peer client started...")
        # connects to the server of other peer
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        # if the server of this peer is not connected by someone else and if this is the requester side peer client then enters here
        if self.peerServer.isChatRequested == 0 and self.responseReceived is None:
            # composes a request message and this is sent to server and then this waits a response message from the server this client connects
            requestMessage = "CHAT-REQUEST " + str(self.peerServer.peerServerPort) + " " + self.username
            # logs the chat request sent to other peer
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + requestMessage)
            # sends the chat request
            self.tcpClientSocket.send(requestMessage.encode())
            print("Request message " + requestMessage + " is sent...")
            # received a response from the peer which the request message is sent to
            self.responseReceived = self.tcpClientSocket.recv(1024).decode()
            # logs the received message
            logging.info(
                "Received from " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + self.responseReceived)
            print("Response is " + self.responseReceived)
            # parses the response for the chat request
            self.responseReceived = self.responseReceived.split()
            # if response is ok then incoming messages will be evaluated as client messages and will be sent to the connected server
            if self.responseReceived[0] == "OK":
                # changes the status of this client's server to chatting
                self.peerServer.isChatRequested = 1
                # sets the server variable with the username of the peer that this one is chatting
                self.peerServer.chattingClientName = self.responseReceived[1]
                # as long as the server status is chatting, this client can send messages
                while self.peerServer.isChatRequested == 1:
                    # message input prompt
                    messageSent = input(self.username + ": ")
                    # sends the message to the connected peer, and logs it
                    self.tcpClientSocket.send(messageSent.encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                    # if the quit message is sent, then the server status is changed to not chatting
                    # and this is the side that is ending the chat
                    if messageSent == ":q":
                        self.peerServer.isChatRequested = 0
                        self.isEndingChat = True
                        break
                # if peer is not chatting, checks if this is not the ending side
                if self.peerServer.isChatRequested == 0:
                    if not self.isEndingChat:
                        # tries to send a quit message to the connected peer
                        # logs the message and handles the exception
                        try:
                            self.tcpClientSocket.send(":q ending-side".encode())
                            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                        except BrokenPipeError as bpErr:
                            logging.error("BrokenPipeError: {0}".format(bpErr))
                    # closes the socket
                    self.responseReceived = None
                    self.tcpClientSocket.close()
            # if the request is rejected, then changes the server status, sends a reject message to the connected peer's server
            # logs the message and then the socket is closed       
            elif self.responseReceived[0] == "REJECT":
                self.peerServer.isChatRequested = 0
                print("client of requester is closing...")
                self.tcpClientSocket.send("REJECT".encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> REJECT")
                self.tcpClientSocket.close()
            # if a busy response is received, closes the socket
            elif self.responseReceived[0] == "BUSY":
                print("Receiver peer is busy")
                self.tcpClientSocket.close()
        # if the client is created with OK message it means that this is the client of receiver side peer
        # so it sends an OK message to the requesting side peer server that it connects and then waits for the user inputs.
        elif self.responseReceived == "OK":
            # server status is changed
            self.peerServer.isChatRequested = 1
            # ok response is sent to the requester side
            okMessage = "OK"
            self.tcpClientSocket.send(okMessage.encode())
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + okMessage)
            print("Client with OK message is created... and sending messages")
            # client can send messsages as long as the server status is chatting
            while self.peerServer.isChatRequested == 1:
                # input prompt for user to enter message
                messageSent = input(self.username + ": ")
                self.tcpClientSocket.send(messageSent.encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                # if a quit message is sent, server status is changed
                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    self.isEndingChat = True
                    break
            # if server is not chatting, and if this is not the ending side
            # sends a quitting message to the server of the other peer
            # then closes the socket
            if self.peerServer.isChatRequested == 0:
                if not self.isEndingChat:
                    self.tcpClientSocket.send(":q ending-side".encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                self.responseReceived = None
                self.tcpClientSocket.close()


# main process of the peer
class peerMain:

    # peer initializations
    def __init__(self):
        # ip address of the registry
        
        self.registryName = input("\033[92mEnter IP address of registry: \033[0m")
        # self.registryName = 'localhost'
        # port number of the registry
        self.registryPort = 15600
        # tcp socket connection to registry
        self.tcpClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpClientSocket.connect((self.registryName, self.registryPort))
        # initializes udp socket which is used to send hello messages
        self.udpClientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        # udp port of the registry
        self.registryUDPPort = 15500
        # login info of the peer
        self.loginCredentials = (None, None)
        # online status of the peer
        self.isOnline = False
        # server port number of this peer
        self.peerServerPort = None
        # server of this peer
        self.peerServer = None
        # client of this peer
        self.peerClient = None
        # timer initialization
        self.timer = None
        self.peerUDPportnumber=None

        choice = "0"
        # log file initialization
        logging.basicConfig(filename="peer.log", level=logging.INFO)
        # as long as the user is not logged out, asks to select an option in the menu
        while choice != "3":

            # menu selection prompt
            choice = input(
                "\033[95mChoose: \nCreate account: -1\nBroadcast: 1\nLogin: 2\nLogout: 3\nSearch: 4\nStart a chat: 5\nPrint list of online users:6\nCreate chat room:7\nJoin chat room:8\nLeave chat room:9\nPrint List of Chat Rooms:10\033[0m\n")
            # if choice is 1, creates an account with the username
            # and password entered by the user
            if choice == "1":
                username = input("username: ")
                password = input("password: ")
                self.createAccount(username, password)
            # todo : for testing purpose-------
            if choice == "-1" and self.isOnline:
                self.test_broadcast()
            # if choice is 2 and user is not logged in, asks for the username
            # and the password to login
            elif choice == "2" and not self.isOnline:
                username = input("username: ")
                password = input("password: ")
                peerServerPort = self.find_available_port(socket.gethostbyname(socket.gethostname()))
                status = self.login(username, password, peerServerPort)
                print("Peer server port is : ", peerServerPort)
                # is user logs in successfully, peer variables are set
                if status == 1:
                    self.isOnline = True
                    self.loginCredentials = (username, password)
                    self.peerServerPort = peerServerPort
                    # creates the server thread for this peer, and runs it
                    self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort)
                    self.peerServer.start()
                    # hello message is sent to registry
                    self.sendHelloMessage()
            # if choice is 3 and user is logged in, then user is logged out
            # and peer variables are set, and server and client sockets are closed
            elif choice == "3" and self.isOnline:
                self.logout(1)
                self.isOnline = False
                self.loginCredentials = (None, None)
                self.peerServer.isOnline = False
                self.peerServer.tcpServerSocket.close()
                if self.peerClient is not None:
                    self.peerClient.tcpClientSocket.close()
                print("\033[31mLogged out successfully\033[0m")

            # is peer is not logged in and exits the program
            elif choice == "3":
                self.logout(2)
            # if choice is 4 and user is online, then user is asked
            # for a username that is wanted to be searched
            elif choice == "4" and self.isOnline:
                username = input("Username to be searched: ")
                searchStatus = self.searchUser(username)
                # if user is found its ip address is shown to user
                if searchStatus != None and searchStatus != 0:
                    print("\033[31mIP address of \033[0m " + username + " \033[31mis \033[0m " + searchStatus)

            elif choice == "6" and self.isOnline:
                self.print_online_users()

            elif choice == "7" and self.isOnline:
                room_name = input("room name: ")
                response= self.Createchatroom(room_name,self.loginCredentials[0],self.peerServer.peerServerHostname ,self.peerServerPort,self.peerUDPportnumberr)
                print(response)

#todo :: Finish this function
            elif choice == "8" and self.isOnline:
                room_names=self.get_chatrooms()
                if ("NO" not in room_names):
                    print("CHOOSE ONE OF THE FOLLOWING CHATROOMS TO ENTER :")
                    room_name = input("room name: ")
                    response=self.joinRoom(room_name,self.loginCredentials[0],self.peerServer.peerServerHostname ,self.peerServerPort,self.peerUDPportnumber)
                    print(response)
                else :
                    print(room_names)
                
            elif choice == "9" and self.isOnline :
                room_name = input("room name: ")
                response=self.leaveRoom(self.loginCredentials[0],room_name)
                print(response)

            elif choice == "10" and self.isOnline:
                self.print_ChatRooms()

            # if choice is 5 and user is online, then user is asked
            # to enter the username of the user that is wanted to be chatted
            elif choice == "5" and self.isOnline:
                username = input("Enter the username of user to start chat: ")
                searchStatus = self.searchUser(username)
                # if searched user is found, then its ip address and port number is retrieved
                # and a client thread is created
                # main process waits for the client thread to finish its chat
                if searchStatus != None and searchStatus!=0:
                    searchStatus = searchStatus.split(":")
                    self.peerClient = PeerClient(searchStatus[0], int(searchStatus[1]), self.loginCredentials[0],self.peerServer, None)
                    self.peerClient.start()
                    self.peerClient.join()

            # if this is the receiver side then it will get the prompt to accept an incoming request during the main loop
            # that's why response is evaluated in main process not the server thread even though the prompt is printed by server
            # if the response is ok then a client is created for this peer with the OK message and that's why it will directly
            # sent an OK message to the requesting side peer server and waits for the user input
            # main process waits for the client thread to finish its chat
            elif choice == "OK" and self.isOnline:
                okMessage = "OK " + self.loginCredentials[0]
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> " + okMessage)
                self.peerServer.connectedPeerSocket.send(okMessage.encode())
                self.peerClient = PeerClient(self.peerServer.connectedPeerIP, self.peerServer.connectedPeerPort,
                                             self.loginCredentials[0], self.peerServer, "OK")
                self.peerClient.start()
                self.peerClient.join()
            # if user rejects the chat request then reject message is sent to the requester side
            elif choice == "REJECT" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("REJECT".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> REJECT")
            # if choice is cancel timer for hello message is cancelled
            elif choice == "CANCEL":
                self.timer.cancel()
                break
        # if main process is not ended with cancel selection
        # socket of the client is closed
        if choice != "CANCEL":
            self.tcpClientSocket.close()

    def hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password
        # account creation function

    def createAccount(self, username, password):
        # join message to create an account is composed and sent to registry
        # if response is success then informs the user for account creation
        # if response is exist then informs the user for account existence
        hashed_password = self.hash_password(password)
        message = "JOIN " + username + " " + hashed_password.decode('utf-8')
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "join-success":
            print("\033[31mAccount created... \033[0m")
        elif response == "join-exist":
            print("\033[31mchoose another username or login... \033[0m")

    # login function
    def login(self, username, password, peerServerPort):
        # a login message is composed and sent to registry
        # an integer is returned according to each response
        message = "LOGIN " + username + " " + password + " " + str(peerServerPort)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "login-success":
            print("\033[93mLogged in successfully...\033[0m")
            return 1
        elif response == "login-account-not-exist":
            print("\033[93mAccount does not exist...\033[0m")
            return 0
        elif response == "login-online":
            print("\033[93mAccount is already online...\033[0m")
            return 2
        elif response == "login-wrong-password":
            print("\033[93mWrong password...\033[0m")
            return 3

    # logout function
    def logout(self, option):
        # a logout message is composed and sent to registry
        # timer is stopped
        if option == 1:
            message = "LOGOUT " + self.loginCredentials[0]
            self.timer.cancel()
        else:
            message = "LOGOUT"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())

    # function for searching an online user
    def searchUser(self, username):
        # a search message is composed and sent to registry
        # custom value is returned according to each response
        # to this search message
        message = "SEARCH " + username
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "search-success":
            print(username + " \033[93mis found successfully...\033[0m")
            return response[1]
        elif response[0] == "search-user-not-online":
            print(username + " \033[93mis not online...\033[0m")
            return 0
        elif response[0] == "search-user-not-found":
            print(username + " \033[93mis not found\033[0m")
            return None

    def Createchatroom(self, room_name,creator_username, creator_ip_address, creator_tcp_port_number,creator_udp_port_number):
        message = "CREATE " + room_name + " " + creator_username +" "+ str(creator_ip_address) + " " + str(creator_tcp_port_number) + " " + str(creator_udp_port_number)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        print(response)

    def joinRoom(self, room_name, username, ip_address, tcp_port_number,udp_port_number):
        message = "JOIN-ROOM "+ room_name + " " + username+" "+ str(ip_address) + " " + str(tcp_port_number) + " " + str(udp_port_number)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        # if response [2] == 'joined' :


        # if response == "MEMBER-JOINED":
        #     print("\033[93mROOM JOINED successfully...\033[0m")
        #     return 2
        # elif response == "JOIN-ROOM-FAIL":
        #     print("\033[93mROOM does not exist...\033[0m")
        #     return 0
        # elif response == "MEMBER-IN-ROOM" :
        #     print("\033[93mMember already in room \033[0m")
        #     return 1

  #todo :: leave room to be handled with list of rooms
    def leaveRoom(self, username,room_name):
        message = "LEAVE "+ username + " " + room_name
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        if response == "USER LEFT":
           logging.info("Received from " + self.registryName + " -> " + response)
           print("YOU LEFT")
        elif response == "USER-NOT-IN-THIS-ROOM ":
           logging.info("Received from " + self.registryName + " -> " + response)
           print("YOU ARE NOT IN THIS ROOM")
        elif response == "ROOM-DOES-NOT-EXIST ":
           logging.info("Received from " + self.registryName + " -> " + response)
           print("Wrong room enterd")


    def print_ChatRooms(self):
        response = self.get_chatrooms()
        print(response)

    def get_chatrooms (self):
        message = "PRINT_CHATROOMS"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        return response

    def print_online_users(self):
        message = "PRINT"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        print(response)

    #def get_members(self,chatroom_name):


    # function for sending hello message
    # a timer thread is used to send hello messages to udp socket of registry
    def sendHelloMessage(self):
        message = "HELLO " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryUDPPort) + " -> " + message)
        self.udpClientSocket.sendto(message.encode(), (self.registryName, self.registryUDPPort))
        self.timer = threading.Timer(20, self.sendHelloMessage)
        self.timer.start()
        peer_udp_port,server_udp_port = self.udpClientSocket.recvfrom(1024)
        self.peerUDPportnumber=peer_udp_port

    def is_port_available(self,ip_no,port,udp=False):
        try:
            if udp :
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.bind((ip_no, port))
                return True
            else :
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((ip_no, port))
                return True
        except socket.error:
            return False
    def find_available_port(self,ip_no,start_port=60000, end_port=65535,udp=False):
        for port in range(start_port, end_port + 1):
            if self.is_port_available(ip_no,port,udp):
                return port
        print("No ports available!")
        return None  # If no available port is found in the specified range

    def test_broadcast(self):
        print("Enter your message :")
        message = input()
        print("Enter member :")
        while ("q" not in message):
            print("Enter member port number:")
            port = input()
            print("Enter member IP number:")
            ip=input()
            self.broadcast_message(message,port,ip)



#todo::Not finished yet
    def broadcast_message_test(self,message,ip,udpport):
        self.udpClientSocket.sendto(message.encode(), (ip,udpport))
    def broadcast_message(self,message,members_list):
         for member in members_list :
             if member["username"] != self.username:
                 self.udpClientSocket.sendto(message.encode(),(member["IP address"],member["UDP_Port_number"]))

main=peerMain()
