from maubot import Plugin
from sqlalchemy import (Column, String, Integer, Table, MetaData, Boolean, and_)
from sqlalchemy.engine.base import Engine


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

    def get_target_by_id(self, row_id: Integer) -> object:
        result = self.db.execute(self.rooms.select().where(self.rooms.c.id == row_id).limit(1)).fetchone()
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
