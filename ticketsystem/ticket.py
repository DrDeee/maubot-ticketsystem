class Ticket:
    id: str

    original_message: str
    original_room: str

    mirror_message: str
    mirror_room: str

    creator: str

    def __init__(self, databaseObject):
        self.id = databaseObject["id"]

        self.original_message = databaseObject["original_message"]
        self.original_room = databaseObject["original_room"]

        self.mirror_message = databaseObject["mirrored_message"]
        self.mirror_room = databaseObject["mirrored_room"]

        self.creator = databaseObject["creator"]