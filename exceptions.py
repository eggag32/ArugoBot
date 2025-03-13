class DatabaseError(Exception):
    def __init__(self, message):
        super().__init__(f"Database error: {message}")
        self.message = message

class RequestError(Exception):
    def __init__(self, message):
        super().__init__(f"Request error: {message}")
        self.message = message