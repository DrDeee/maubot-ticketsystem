from maubot import Plugin

from .databases import SupportRoomDatabase, TicketDatabase
from .listener import TicketListener, RoomRegisterCommands


class TicketSystemPlugin(Plugin):
    roomDB: SupportRoomDatabase
    ticketDB: TicketDatabase

    async def start(self) -> None:
        self.log.info("Starting TicketSystem..")
        self.roomDB = SupportRoomDatabase(self.database, self)
        self.ticketDB = TicketDatabase(self.database, self)

        self.register_handler_class(RoomRegisterCommands(self.roomDB, self))
        self.register_handler_class(TicketListener(self, self.roomDB, self.ticketDB))
        self.log.info("TicketSystem started.")
