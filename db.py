from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# define PY_SSIZE_T_CLEAN
# Includes database operations
class DB:

    # db initializations
    def __init__(self):

        self.client = MongoClient('mongodb://localhost:27017')
        self.db = self.client['p2p-chat']

    # checks if an account with the username exists
    def is_account_exist(self, username):
        return self.db.accounts.count_documents({'username': username}) > 0

    # registers a user
    def register(self, username, password):
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)

    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]

    # checks if an account with the username online
    def is_account_online(self, username):
        return self.db.online_peers.count_documents({"username": username}) > 0

    # logs in the user
    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)

    # logs out the user
    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})

    # retrieves the ip address and the port number of the username
    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"])

    def delete_all_online_peers(self):
        # Delete all documents in the 'online_peers' collection
        self.db.online_peers.delete_many({})

    def save_chatroom(self, room_name):

        chatroom_data = {
            "room_name": room_name,
            "members": []
        }
        existing_room = self.db.chatrooms.find_one({"room_name": room_name})
        if existing_room is not None:
            return f"Chatroom with name '{room_name}' already exists."
        else:
            try:
                self.db.chatrooms.insert_one(chatroom_data)
                return f"Chatroom '{room_name}' created successfully."
            except Exception as e:
                return f"Error creating chatroom '{room_name}': {e}"


    def add_member(self, room_name, username, ip_address, tcp_port_number,udp_port_number):
            member_data = {
                "username": username,
                "IP address": ip_address,
                "TCP_Port_number": tcp_port_number,
                "UDP_Port_number" : udp_port_number
            }

            # Check if the user is not already a member of the chatroom
            if not self.is_member_inroom(username)[0]:
                try:
                    self.db.chatrooms.update_one(
                        {"room_name": room_name},
                        {'$addToSet': {'members': member_data}}
                    )
                    return (f"Member '{username}' joined the chatroom '{room_name}' successfully.")
                except Exception as e:
                    return (f"Error adding member '{username}' to chatroom '{room_name}': {e}")
            else:
                return(f"Member '{username}' is already in the chatroom '{room_name}'.")

    def is_room_exits(self, room_name):
        try:
            # Check if a chatroom with the given name exists
            count = self.db.chatrooms.count_documents({'room_name': room_name})
            if (count):
                return count > 0 , (f"ROOM {room_name} EXISTS ")
            else :
                return count > 0, (f"ROOM {room_name} DOES NOT EXIST")
        except Exception as e:
            return False,(f"Error checking chatroom existence for '{room_name}': {e}")


    def leave_room(self,username,room_name):
            try:
                self.db.chatrooms.update_one(
                    {"room_name": room_name},
                    {'$pull': {'members': {'username': username}}}
                )
                return (f"Member '{username}' removed from the chatroom '{room_name}' successfully.")
            except Exception as e:
                return (f"Error removing member '{username}' from chatroom '{room_name}': {e}")


    def is_member_inroom(self, username):
            try:
                # Find the chatroom where the user is a member
                chatroom = self.db.chatrooms.find_one({"members.username": username})

                if chatroom is not None:
                    # Extract the room_name from the chatroom document
                    room_name = chatroom.get("room_name", None)
                    return True, room_name
                else:
                    return False, None

            except Exception as e:
                print(f"Error checking membership for '{username}': {e}")
                return False, None


    def get_all_chatroom_names(self):
            try:
                # Find all documents in the chatrooms collection
                cursor = self.db.chatrooms.find({}, {"room_name": 1, "_id": 0})

                # Extract chatroom names from the cursor
                chatroom_names = [chatroom["room_name"] for chatroom in cursor]

                if len(chatroom_names):
                    return list(chatroom_names)
                else:
                    return "NO CHATROOMS HAVE BEEN CREATED YET"
            except Exception as e:
                return f"Error getting chatroom names: {e}"


    def get_chatroom_members(self, room_name):
            # Query the chatrooms collection to find the specified chatroom
            chatroom = self.db.chatrooms.find_one({"room_name": room_name})
            if len(chatroom["members"]):
                # Extract the members from the chatroom document
                members = chatroom.get("members", [])
                return members
            else:
                return f"Member not found."

    def remove_member(self,username,room_name):
        try:
            self.db.chatrooms.update_one(
            {"room_name": room_name},
            {'$pull': {'members': {'username': username}}})
            return (f"Member '{username}' removed from the chatroom '{room_name}' successfully.")
        except Exception as e:
             return (f"Error removing member '{username}' from chatroom '{room_name}': {e}")

    def delete_all_members(self):
        try:
            # Find all documents in the chatrooms collection
            cursor = self.db.chatrooms.find({}, {"room_name": 1, "_id": 0})

            # Iterate through each chatroom and remove all members
            for chatroom in cursor:
                room_name = chatroom.get("room_name", None)
                if room_name:
                    self.db.chatrooms.update_one(
                        {"room_name": room_name},
                        {'$set': {'members': []}}
                    )
            return "All members in all rooms have been deleted successfully."
        except Exception as e:
            return f"Error deleting all members in all rooms: {e}"

    
    
