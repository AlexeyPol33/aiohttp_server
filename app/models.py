
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
from dotenv import load_dotenv
import asyncio
import enum
import os

load_dotenv()

DB_USER_NAME = os.getenv('DB_USER_NAME', default='postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', default='postgres')
DB_NAME = os.getenv('DB_NAME',default='test')
DB_HOST = os.getenv('DB_HOST',default='localhost')
DB_PORT = os.getenv('DB_PORT',default='5432')
DNS = f'postgresql+asyncpg://\
{DB_USER_NAME}:\
{DB_PASSWORD}@\
{DB_HOST}:\
{DB_PORT}/\
{DB_NAME}'

engine = create_async_engine(DNS, echo = False)

Session = sessionmaker(engine, class_= AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Role(enum.Enum):
    
    user = 'user'
    admin = 'admin'
    def __str__(self):
        return self.value


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False,unique=True,index=True)
    password = Column(String, nullable=False)
    email = Column(String,nullable=True)
    role = Column(Enum(Role), default=Role.user, nullable=False)
    create_time = Column(DateTime, server_default=func.now())
    advertisements = relationship('Advertisements', secondary='user_advertisements', back_populates='user', overlaps="advertisements,user")

class Advertisements(Base):
    __tablename__ = 'advertisements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable= False)
    description = Column(String, nullable= False)
    create_time = Column(DateTime, server_default=func.now())
    user = relationship('Users', secondary='user_advertisements', back_populates='advertisements', overlaps="advertisements,user")

class UserAdvertisements(Base):
    __tablename__ = 'user_advertisements'

    id = Column(Integer, primary_key=True,autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    advertisement_id = Column(Integer, ForeignKey('advertisements.id'))

    user = relationship('Users', backref=backref('user_advertisements', cascade='all, delete-orphan'), overlaps="advertisements,user")
    advertisement = relationship('Advertisements', backref=backref('user_advertisements', cascade='all, delete-orphan'), overlaps="advertisements,user")

meta = MetaData()

async def run_db():
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.drop_all)
        await con.run_sync(Base.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(run_db())

