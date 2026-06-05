import json
import os

class SessionManager:
    DB_FILE = "storage_auth.json"

    def __init__(self):
        if not os.path.exists(self.DB_FILE):
            with open(self.DB_FILE, 'w') as f:
                json.dump({"admin": "admin123"}, f)

    def authenticate(self, username, password):
        with open(self.DB_FILE, 'r') as f:
            users = json.load(f)
        return users.get(username) == password

    def register_user(self, username, password):
        with open(self.DB_FILE, 'r') as f:
            users = json.load(f)
        if username in users:
            return False, "User already exists."
        users[username] = password
        with open(self.DB_FILE, 'w') as f:
            json.dump(users, f)
        return True, "Success"