class SimEvent:
    def __init__(self, type, room_id, payload=None):
        self.type = type
        self.room_id = room_id
        self.payload = payload or {}