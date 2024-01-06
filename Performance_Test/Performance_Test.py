import random
import threading
import time
import Peer_test

class Performance_Test():
    def __init__(self, rooms_count, peers_per_room):
        self.peers = []
        self.rooms = []
        self.rooms_count = rooms_count
        self.peers_per_room = peers_per_room
        self.signup_times = []
        self.room_creation_times = []

    def signup_login(self, number_of_peers):
        for i in range(number_of_peers):
            start_time = time.time()
            username = f"peer_{i}"
            password = "password"
            peer = Peer_test.peerMain
            peer.createAccount(username, password)
            port_number = peer.find_available_port(peer.registryName)
            peer.login(username,password, port_number)
            self.peers.append(peer)
            end_time = time.time()
            self.signup_times.append(end_time - start_time)
            print(f'Peer{i} has signed up and joined successfully')

    def create_chatroom(self):
        for room_id in range(self.rooms_count):
            start_time = time.time()
            join_index = self.rooms_count * room_id
            print(f'Join-index of {join_index}')
            creator_peer = self.peers[join_index]
            room_name = f'room_{room_id}'
            response=creator_peer.Createchatroom(room_name)
            if("created" in response):
                self.rooms.append(room_name)
                for peer_id in range(join_index, join_index + self.peers_per_room):
                    joiner_peer = self.peers[peer_id]
                    joiner_peer.joinRoom_test(room_name, "peer_" + str(peer_id), joiner_peer.registryName,
                                       joiner_peer.peerServerPort, joiner_peer.peerUDPportnumber)

                    print(f'Peer{peer_id} has joined the room{room_name} successfully')
            end_time = time.time()
            self.room_creation_times.append(end_time - start_time)
    #100 peer
    # 10 rooms: 0-9 -- remaining = 90
    # 10 creators: peers 0-9
    # room0: 0-9
    # room1: 10-19
    # room2: 20:29
    # room3: 30:26
    # room9: 90:99

    # def send_messages(self):
    #     for room_id in range(self.rooms_count):
    #         join_index = self.rooms_count * room_id
    #         for peer_id in range(join_index, join_index + self.peers_per_room - 1):
    #             peer = self.peers[peer_id]
    #             message = "HELLO FROM : " + str(peer_id)
    #             room_peers = self.peers[join_index: (join_index + self.peers_per_room)]
    #             peer.broadcast_message(message, room_peers)
    #             print(f'Peer{peer_id} sent {message} to other peers')

    def run_parallel_signups(self, number_of_peers):
        threads = []
        for i in range(number_of_peers):
            thread = threading.Thread(target=self.signup_login, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def run_parallel_room_creation(self, num_rooms):
        threads = []
        for i in range(num_rooms):
            thread = threading.Thread(target=self.create_chatroom, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def calculate_metrics(self, times):
        min_time = min(times)
        max_time = max(times)
        avg_time = sum(times) / len(times)
        return min_time, max_time, avg_time

    def print_results(self, total_time):
        min_signup_time, max_signup_time, avg_signup_time = self.calculate_metrics(self.signup_times)
        min_room_time, max_room_time, avg_room_time = self.calculate_metrics(self.room_creation_times)

        print("Performance Results for 500 PEERS at the same time:")
        print("-" * 60)
        print("{:<30} {:<15}".format("Metric", "Time (seconds)"))
        print("-" * 60)
        print("{:<30} {:<15}".format("Min Signup Time", min_signup_time))
        print("{:<30} {:<15}".format("Max Signup Time", max_signup_time))
        print("{:<30} {:<15}".format("Avg. Signup Time", avg_signup_time))
        print("{:<30} {:<15}".format("Min Create Chatroom Time", min_room_time))
        print("{:<30} {:<15}".format("Max Create Chatroom Time", max_room_time))
        print("{:<30} {:<15}".format("Avg. Create Chatroom Time", avg_room_time))
        print("{:<30} {:<15}".format("Total Execution Time From Signup to Joining Rooms (FOR ALL PEERS)s", total_time))
        print("-" * 60)

    def run_test(self, number_of_peers):
        start_time = time.time()
        self.signup_login(number_of_peers)
        self.create_chatroom()
        #self.send_messages()
        end_time = time.time()
        total_time = end_time - start_time
        self.print_results(total_time)


rooms_count = 100
peers_per_room = 5
tester = Performance_Test(rooms_count, peers_per_room)
tester.run_test(500)