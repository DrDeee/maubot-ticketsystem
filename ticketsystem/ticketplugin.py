from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from mautrix.types import EventType, RoomDirectoryVisibility, RoomCreatePreset

from ticketsystem.database import SupportRoomDatabase


class TicketSystemPlugin(Plugin):
    db: SupportRoomDatabase

    async def start(self) -> None:
        self.db = SupportRoomDatabase(self.database, self)

    @command.new("support", require_subcommand=True)
    async def support(self, evt: MessageEvent) -> None:
        pass

    @support.subcommand("init", help="Initiiert den Support für diesen Raum.\nSyntax: `!support init "
                                     "<Anzeigename>`")
    @command.argument("name", label="Anzeigename", required=True, pass_raw=True)
    async def init(self, evt: MessageEvent, name: str) -> None:
        levels = await self.client.get_state_event(evt.room_id, EventType.ROOM_POWER_LEVELS)
        user_level = levels.get_user_level(evt.sender)

        if user_level < 100:
            await evt.reply("Du musst mindestens Powerlevel 100 (Adiministrator) haben, um den Support zu initiieren.")
            return
        if name is None or name == "":
            await evt.reply("Usage: `!support init <Anzeigename>`:\n\n"
                            "- `Anzeigename`: mit diesem Namen wird der Raum in der Supportliste angezeigt")
        else:
            if self.db.create_new_room(evt.room_id, name):
                await evt.reply(
                    "Dieser Raum wurde erfolgreich mit dem Namen \"" + name
                    + "\" in das Support-Register eingetragen. Matrix-Nutzer können dich nun erreichen.")
            else:
                if self.db.get_target_by_room_id(evt.room_id) is not None:
                    await evt.reply("Es ist bereit ein Raum mit dem Namen \"" + name
                                    + "\" ins Support-Register eingetragen. Bitte wähle dir einen anderen Namen.")
                else:
                    await evt.reply("Für diesen Raum exsistiert bereits ein Eintrag im Support-Register!")

    @support.subcommand("lock",
                        help="Versteckt diesen Raum aus der Support-Liste. "
                             "Der Eintrag bleibt zwar exsistent, aber man kann euch keine Support-Anfragen "
                             "mehr senden. Verwende `!support unlock` um diesen Raum wieder zu öffnen")
    async def lock(self, evt: MessageEvent):
        if self.db.get_target_by_room_id(evt.room_id) is None:
            await evt.reply("Für diesen Raum exsistiert kein Eintrag im Support-Register. "
                            "Registriere diesen Raum mit `!support init`")
        else:
            if self.db.is_locked(evt.room_id) is not True:
                self.db.lock_room_by_room_id(evt.room_id)
                await evt.reply("Dieser Raum ist nun für Support-Anfragen geschlossen. "
                                "Öffne ihn wieder mit `!support unlock`")
            else:
                await evt.reply("Dieser Raum ist bereits geschlossen!")

    @support.subcommand("unlock",
                        help="Zeige diesen Raum wieder in der Support-Liste. ")
    async def unlock(self, evt: MessageEvent):
        if self.db.get_target_by_room_id(evt.room_id) is None:
            await evt.reply("Für diesen Raum exsistiert kein Eintrag im Support-Register. "
                            "Registriere diesen Raum mit `!support init`")
            return
        else:
            if self.db.is_locked(evt.room_id):
                self.db.unlock_room_by_room_id(evt.room_id)
                await evt.reply("Dieser Raum ist nun für Support-Anfragen geöffnet. "
                                "Schließe ihn wieder mit `!support lock`")
            else:
                await evt.reply("Dieser Raum ist gar nicht geschlossen.")

    @support.subcommand("destroy",
                        help="Löscht den Eintrag im Support-Register. Dadurch kann man euch nicht mehr erreichen und "
                             "der Name ist wieder für andere freigegeben.")
    @command.argument("sure", pass_raw=False)
    async def destroy(self, evt: MessageEvent, sure: str):
        levels = await self.client.get_state_event(evt.room_id, EventType.ROOM_POWER_LEVELS)
        user_level = levels.get_user_level(evt.sender)
        if user_level < 100:
            await evt.reply("Du musst mindestens Powerlevel 100 (Adiministrator) haben, um den Support-Eintrag zu "
                            "löschen.")
            return
        if self.db.get_target_by_room_id(evt.room_id) is None:
            await evt.reply("Für diesen Raum gibt es keinen Eintrag im Support-Register.")
            return
        if sure == "jaichwilldeneintraglöschen":
            self.db.delete_target_room_by_room_id(evt.room_id)
            await evt.reply("Der Eintrag im Support-Register wurde erfolgreich gelöscht.")
        else:
            await evt.reply("Um sicherzugehen, dass du den Raum absichtlich löschst, gebe bitte hinter `!support "
                            "destroy` noch `jaichwilldeneintraglöschen` ein.")
