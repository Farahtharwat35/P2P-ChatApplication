from pymongo import MongoClient

# Includes database operations
class DB:


    # db initializations
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['p2p-chat']


    # checks if an account with the username exists
    def is_account_exist(self, username):
        if self.db.accounts.count_documents({'username': username}) > 0:
            return True
        else:
            return False
    

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
        if self.db.online_peers.count_documents({"username": username}) > 0:
            return True
        else:
            return False

    
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
    
    def savechatroom(self, room_name):
      chatroom_data = {
        "room_name": room_name,
        "members" : []   
    } 
      self.db.chatrooms.insert_one(chatroom_data)


    def appendmembers(self, room_name, username):
        self.db.chatrooms.update_one({"room_name":room_name},{'$addToSet':{'members':username}})

    def is_room_exits(self, room_name):
        if self.db.chatrooms.count_documents({'room_name': room_name}) > 0:
            return True
        else:
            return False

    def LEAVE_ROOM(self,username):
        self.db.chatrooms.update_one({"room_name":self.room_name},{'$pull':{'members':username}})  

    def is_member_inroom(self,room_name,username):
        room = self.db.chatrooms.find_one({"room_name": room_name})
        mem = room.get("members",[])
        # userinroom = ', '.join(str(mems) for mems in mem)
        for user in mem:
            if(user==username):
                return 1
        return 0