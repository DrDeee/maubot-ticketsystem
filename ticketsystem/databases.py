import collections
from typing import Dict, List

from maubot import Plugin
from mautrix.types import MessageEvent
from sqlalchemy import (Column, String, Integer, Table, MetaData, Boolean, and_)
from sqlalchemy.engine.base import Engine

from ticketsystem.ticket import Ticket


class SupportRoom:
    display_name: str
    room_id: str
    internal_id: str

    def __init__(self, name: str, room_id: str, internal_id: str):
        self.display_name = name
        self.room_id = room_id
        self.internal_id = internal_id


class SupportRoomDatabase:
    rooms: Table
    db: Engine
    plugin: Plugin

    def __init__(self, db: Engine, plugin: Plugin) -> None:
        self.db = db
        self.plugin = plugin

        meta = MetaData()
        meta.bind = db

        self.rooms = Table("support_targets", meta,
                           Column("id", Integer, primary_key=True, autoincrement=True),
                           Column("room_id", String(255), nullable=True),
                           Column("display_name", String(255), nullable=False),
                           Column("locked", Boolean, nullable=False))
        meta.create_all()

    def create_new_room(self, room_id: String, display_name: String) -> bool:
        if (self.db.execute(self.rooms.select().where(
                and_(
                    self.rooms.c.display_name == display_name, self.rooms.c.room_id == room_id)))).fetchone() is None:
            self.db.execute(self.rooms.insert().values(room_id=room_id, display_name=display_name, locked=False))
            return True
        else:
            return False

    def get_target_by_id(self, room_id: Integer) -> object:
        result = self.db.execute(self.rooms.select().where(self.rooms.c.id == room_id).limit(1)).fetchone()
        return result

    def get_target_by_room_id(self, room_id: str) -> object:
        result = self.db.execute(self.rooms.select().where(self.rooms.c.room_id == room_id).limit(1)).fetchone()
        return result

    def lock_room_by_room_id(self, room_id: str):
        self.db.execute(self.rooms.update().where(self.rooms.c.room_id == room_id).values(locked=True))

    def unlock_room_by_room_id(self, room_id: str):
        self.db.execute(self.rooms.update().where(self.rooms.c.room_id == room_id).values(locked=False))

    def is_locked(self, room_id: str) -> Boolean:
        room = self.get_target_by_room_id(room_id)
        if room is None:
            return True
        else:
            return room.locked

    def delete_target_room_by_room_id(self, room_id):
        self.db.execute(self.rooms.delete().where(self.rooms.c.room_id == room_id))

    def get_target_rooms(self) -> List[SupportRoom]:
        data = self.db.execute(self.rooms.select().where(self.rooms.c.locked == False)).fetchall()
        rooms = []
        for row in data:
            rooms.append(SupportRoom(row["display_name"], row["room_id"], row["id"]))
        rooms.sort(key=lambda obj: obj.display_name)
        return rooms


class TicketDatabase:
    tickets: Table
    db: Engine
    plugin: Plugin

    def __init__(self, db: Engine, plugin: Plugin) -> None:
        self.db = db
        self.plugin = plugin

        meta = MetaData()
        meta.bind = db

        self.tickets = Table("tickets", meta,
                             Column("id", Integer, primary_key=True, autoincrement=True),
                             Column("original_room", String(255), nullable=False),
                             Column("original_message", String(255), nullable=False),
                             Column("mirrored_message", String(255), nullable=False),
                             Column("mirrored_room", String(255), nullable=False),
                             Column("creator", String(255), nullable=False))
        meta.create_all()

    def create_new_ticket(self, original_message: str, original_room: str, mirror_message: str, mirror_room: str,
                          creator: str):
        self.plugin.log.debug(f"{original_message} {original_room} {mirror_message} {mirror_room} + {creator}")
        self.db.execute(self.tickets.insert().values(original_room=original_room,
                                                     original_message=original_message,
                                                     mirrored_message=mirror_message,
                                                     mirrored_room=mirror_room,
                                                     creator=creator))

    def get_ticket_by_original_message(self, original_message: str, original_room: str):
        return Ticket(
            self.db.execute(self.tickets.select().where(and_(self.tickets.c.original_message == original_message,
                                                             self.tickets.c.original_room == original_room))) \
                .fetchOne())

    def get_ticket_by_mirror_message(self, mirror_message: str, mirror_room: str):
        return Ticket(
            self.db.execute(self.tickets.select().where(and_(self.tickets.c.mirrored_message == mirror_message,
                                                             self.tickets.c.mirrored_room == mirror_room))) \
                .fetchOne())

    def delete_ticket_by_id(self, identifier):
        self.db.execute(self.tickets.delete().where(self.tickets.c.id == identifier))
