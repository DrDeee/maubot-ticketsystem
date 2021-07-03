from maubot import Plugin

from .databases import SupportRoomDatabase, TicketDatabase
from .listener import TicketListener, RoomRegisterCommands


class TicketSystemPlugin(Plugin):
    roomDB: SupportRoomDatabase
    ticketDB: TicketDatabase

    async def start(self) -> None:
        self.client
        self.log.info("Starting TicketSystem..")
        self.roomDB = SupportRoomDatabase(self.database, self)
        self.ticketDB = TicketDatabase(self.database, self)

        room_register_commands = RoomRegisterCommands(self.roomDB, self)
        ticket_listener = TicketListener(self, self.roomDB, self.ticketDB)

        self.register_handler_class(room_register_commands)
        self.register_handler_class(ticket_listener)
        self.log.info("TicketSystem started.")
