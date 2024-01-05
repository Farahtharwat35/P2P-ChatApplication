'''
    ##  Implementation of peer
    ##  Each peer has a client and a server side that runs on different threads
    ##  150114822 - Eren Ulaş
'''
import asyncio
import atexit
import socket
import threading
import select
import logging
import bcrypt
import pickle




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
                                message = "PEER IS BUSY ! "
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
           # print("Response is " + self.responseReceived)
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
                    messageSent = input()
                    if(messageSent != " "):
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
                messageSent = input()
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
class peerMain():

    # peer initializations
    def __init__(self):
        # ip address of the registry
        
        self.registryName = socket.gethostbyname(socket.gethostname())
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
        #list of room members containing their info (username,ip address and port numbers)
        self.list_of_members= []
        # Register cleanup function with atexit
        atexit.register(self.cleanup)

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
        message = "#" + "JOIN " + username + " " + hashed_password.decode('utf-8')+ "#"
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
        message = "#" + "LOGIN " + username + " " + password + " " + str(peerServerPort)+"#"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        print("\033[93mLogged in successfully...\033[0m")
        self.isOnline = True
        self.loginCredentials = (username, password)
        self.peerServerPort = peerServerPort
        # # creates the server thread for this peer, and runs it
        # self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort)
        # self.peerServer.start()

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

    def Createchatroom(self, room_name):
        message = "#" + "CREATE" + " " + room_name + "#"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        print("CREATION MESSAGE : " , message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024)
        try:
            response = response.decode('utf-8')
        except UnicodeDecodeError:
            # Handle non-UTF-8 data, e.g., by ignoring invalid bytes
            response = response.decode('utf-8', errors='ignore')
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        return response

    def joinRoom_test(self, room_name, username, ip_address, tcp_port_number,udp_port_number):
        message = "JOIN-ROOM "+ room_name + " " + username+" "+ str(ip_address) + " " + str(tcp_port_number) + " " + str(udp_port_number)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024)
        return response
        # recieve_tcpthread=threading.Thread(target=self.recieve_tcp)
        # recieve_tcpthread.start()
        # recieve_udp_thread = threading.Thread(target=self.recieve_udp)
        # recieve_udp_thread.start()

        #self.peerServer.isChatRequested=1
        # recieve_udp_thread.join()  # Wait for the thread to complete before moving on
        # recieve_tcpthread.join()


    def joinRoom(self, room_name, username, ip_address, tcp_port_number,udp_port_number):
        message = "JOIN-ROOM " + room_name + " " + username + " " + str(ip_address) + " " + str(
            tcp_port_number) + " " + str(udp_port_number)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())

        recieve_tcpthread = threading.Thread(target=self.recieve_tcp)
        recieve_tcpthread.start()
        recieve_udp_thread = threading.Thread(target=self.recieve_udp)
        recieve_udp_thread.start()
        #self.peerServer.isChatRequested = 1
        recieve_udp_thread.join()  # Wait for the thread to complete before moving on
        recieve_tcpthread.join()
        message = " "
        while "leave" not in message:
            self.broadcast_message(message, self.list_of_members)
            message = input()
        self.leaveRoom(self.loginCredentials[0],room_name)
        recieve_udp_thread.join()  # Wait for the thread to complete before moving on
        recieve_tcpthread.join()
        #self.peerServer.isChatRequested = 0

    def recieve_tcp(self):
        tcpSocket = self.tcpClientSocket
        inputs = [tcpSocket]
        self.is_inroom = True
        while self.is_inroom:
            #listens to the server
            readable, _, _ = select.select(inputs, [], [])
            for s in readable:
                message = s.recv(4096)
                try:
                    # Try to decode the message as a string
                    message_decoded=message.decode()
                    # Handle different types of messages
                    if message_decoded.startswith("MEMBER-JOINED"):
                        # Extract relevant information
                        data = message_decoded.split()
                        username = data[1]
                        ip_address = data[2]
                        udp_port_number = data[3]
                        # Create member_data dictionary
                        new_member = {
                            "username": username,
                            "IP address": ip_address,
                            "UDP_Port_number": udp_port_number
                        }
                        self.list_of_members.append(new_member)
                        print(f"{username} has joined the room")
                    elif ("You joined the room" in message_decoded) or ("left" in message_decoded) or ("first member to join" in message_decoded):
                        print(message_decoded)
                    elif "YOU LEFT THE ROOM" in message_decoded:
                        print("YOU LEFT THE ROOM")
                        self.is_inroom = False
                        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        udpSocket.sendto(message_decoded.encode(),(socket.gethostbyname(socket.gethostname()),self.peerUDPportnumber))
                        udpSocket.close()
                    elif "Peer-LEFT" in message_decoded:
                        username_left = message_decoded.split()[1]
                        print(f"{username_left} has left the chatroom")
                        # Use a list comprehension to create a new list excluding the member with the specified username
                        self.list_of_members = [member for member in self.list_of_members if
                                                member["username"] != username_left]
                except UnicodeDecodeError:
                    # Handle non-decodable messages (assumed to be binary pickled data)
                    try:
                        received_members_list = pickle.loads(message)
                        self.list_of_members = received_members_list
                        print("You joined the room , start chatting !")
                    except pickle.PickleError as e:
                        print(f"Error deserializing data: {e}")

        return

    def recieve_udp(self):
        udpSocket = self.udpClientSocket
        inputs = [udpSocket]
        while self.is_inroom:
            try:
                readable, _, _ = select.select(inputs, [], [])
                if readable:
                    message_received, clientAddress = udpSocket.recvfrom(1024)
                    message_received = message_received.decode()
                    if("YOU LEFT THE ROOM" in message_received):
                        break
                    username = self.get_username_by_port(int(clientAddress[1]))
                    print(f'{username}: {message_received}')

            except Exception as e:
                print(f"Error in recieve_udp: {e}")
        return

    def leaveRoom(self, username,room_name):
        message = "LEAVE "+ username + " " + room_name
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        return

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

    # function for sending hello message
    # a timer thread is used to send hello messages to udp socket of registry
    def sendHelloMessage(self):
        message = "HELLO " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryUDPPort) + " -> " + message)
        self.udpClientSocket.sendto(message.encode(), (self.registryName, self.registryUDPPort))
        self.timer = threading.Timer(20, self.sendHelloMessage)
        self.timer.start()
        return "done"

    def set_udp_peer_portnumber(self):
        message = "PORTNUMBER"
        self.tcpClientSocket.send(message.encode())
        peer_udp_port= self.tcpClientSocket.recv(1024).decode()
        self.peerUDPportnumber = int(peer_udp_port)
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

    def get_username_by_port(self, target_port):
        for member in self.list_of_members:
            if member.get('UDP_Port_number') == str(target_port):
                return member.get('username')

    def broadcast_message(self,message,members_list):
     for member in members_list :
         if member["username"] != self.loginCredentials[0]:
             self.udpClientSocket.sendto(message.encode(),(member["IP address"],int(member["UDP_Port_number"])))

    def cleanup(self):
        print("Performing cleanup...")
        try:
            self.tcpClientSocket.close()
            self.udpClientSocket.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            print("Cleanup completed.")

peerMain= peerMain()