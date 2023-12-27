# import ipaddress
# import random

# def generate_random_multicast_ip():
#     # Define the multicast IP address range
#     start_ip = ipaddress.IPv4Address('224.0.0.0')
#     end_ip = ipaddress.IPv4Address('230.255.255.255')

#     # Generate a random IP address within the specified range
#     random_ip = ipaddress.IPv4Address(random.randint(int(start_ip), int(end_ip)))

#     return str(random_ip)

# Example usage
##random_multicast_ip = generate_random_multicast_ip()
# print("Random Multicast IP:", random_multicast_ip)


class ChatRoom:
    def __init__(self, room_name, ipaddress):
        self.room_name = room_name
        self.ipaddress= ipaddress
        self.members = set()

    def join(self, username):
        self.members.add(username)

    def leave(self, username):
        self.members.remove(username)

    def broadcast(self, sender, message):
        for member in self.members:
            if member != sender:
                yield member, message