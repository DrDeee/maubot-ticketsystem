import time

from maubot import Plugin
from maubot.handlers import event, command
from maubot.matrix import MaubotMatrixClient
from mautrix.errors import MNotFound
from mautrix.types import EventType, MessageEvent, RelationType, MessageType, StateEvent, Membership

from .databases import SupportRoomDatabase, TicketDatabase


class TicketListener:
    client: MaubotMatrixClient
    plugin: Plugin
    rDB: SupportRoomDatabase
    tDB: TicketDatabase

    ticket_queue: dict = {}

    def __init__(self, plugin: Plugin, roomDB: SupportRoomDatabase, ticketDB: TicketDatabase):
        self.client = plugin.client
        self.plugin = plugin
        self.rDB = roomDB
        self.tDB = ticketDB

    @event.on(EventType.ROOM_MEMBER)
    async def on_member(self, evt: StateEvent):
        if evt.content.membership is not Membership.INVITE and evt.state_key is not self.client.mxid:
            return
        time.sleep(3)
        direct = await self.client.get_account_data(EventType.DIRECT)
        rooms = []
        for user in direct:
            for key in direct[user]:
                rooms.append(key)
        if evt.room_id in rooms:
            await self.plugin.client.send_notice(evt.room_id,
                                                 "Hey, willkommen beim Support Bot"
                                                 "von Fridays for Future Deutschland hier auf Matrix! Um ein Ticket "
                                                 "zu verfassen sende mir einfach eine Nachricht mit dem Inhalt und "
                                                 "ich werde dir alles weitere erklären.")

    @event.on(EventType.ROOM_MESSAGE)
    async def on_message(self, evt: MessageEvent):
        try:
            direct_rooms = await self.client.get_account_data(EventType.DIRECT)
            if evt.sender in direct_rooms and evt.room_id in direct_rooms[evt.sender]:
                if evt.content.relates_to.rel_type is RelationType.REPLY:
                    if evt.room_id in self.ticket_queue:
                        self.plugin.log.debug("Hallo")
                        ticket = self.ticket_queue[evt.room_id]
                        target_room = self.rDB.get_target_by_id(evt.content.body)
                        if target_room is None:
                            await evt.respond(
                                "Dies scheint keine gültige ID zu sein. Versuche es nochmal! "
                                "Antworte dieses Mal auf diese Nachricht")
                            return
                        msg = f"<b><h5>Neues Ticket:<h5></b><hr>{ticket['content']}<hr><em>Gesendet " \
                              f"von {ticket['creator']}. "

                        mirror_msg = await self.plugin.client.send_text(target_room["room_id"], None, msg)
                        self.tDB.create_new_ticket(ticket["original_msg"], evt.room_id, mirror_msg,
                                                   target_room["room_id"], ticket["creator"])
                        await evt.respond("Dein Ticket wurde übermittelt. Du wirst hier so schnell wie es geht "
                                          "eine Antwort erhalten.")
                        del self.ticket_queue[evt.room_id]

                elif evt.content.relates_to.rel_type is None:
                    self.plugin.log.debug("TEst")
                    if self.ticket_queue.get(evt.room_id) is not None:
                        await evt.respond("Bitte schließe erst das Erstellen eines Tickets ab, bevor du ein "
                                          "weiteres erstellst!")
                    else:
                        if evt.content.msgtype is not MessageType.TEXT:
                            await evt.respond("Bitte nutze nur Text für dein Ticket!")
                            return
                        rooms = self.rDB.get_target_rooms()
                        msg = "*Bitte antworte mit der ID der Gruppe, an die das Ticket gesendet werden soll:*\n"
                        for index, value in enumerate(rooms):
                            msg += f"\n{index + 1}. {value.display_name} - ID: **{value.internal_id}**"
                        await evt.respond(msg)
                        if evt.content.formatted_body is not None:
                            msg = evt.content.formatted_body
                        else:
                            msg = evt.content.body
                        self.ticket_queue[evt.room_id] = {
                            "original_msg": evt.event_id,
                            "original_room": evt.room_id,
                            "content": msg,
                            "creator": evt.sender
                        }

        except MNotFound:
            self.plugin.log.error("m.direct isn't set! You have to use https://github.com/drdeee/maubot-dmutil")


class RoomRegisterCommands:
    db: SupportRoomDatabase
    client: MaubotMatrixClient

    def __init__(self, db: SupportRoomDatabase, plugin: Plugin):
        self.db = db
        self.client = plugin.client

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
