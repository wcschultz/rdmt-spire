import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from .base import Base

# This file contains the original tables in the RDMT-Spire sandbox database. 
# Once the new database tables are established and the v0.1 infrastructure is 
# removed we will remove these tables

class TestV2DevTable(Base):
    __tablename__ = "Testv2dev"
    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
        'mysql_default_charset': 'utf8mb4',
        'mysql_engine': 'InnoDB'
    }
    Filename = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    Time = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    ObsID = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=False)
    Detector = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=False)
    Monitors = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)
    MonitorsFail = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)

class V2DevTable(Base):
    __tablename__ = 'v2dev'
    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
        'mysql_default_charset': 'utf8mb4',
        'mysql_engine': 'InnoDB'
    }
    Time = sa.Column(mysql.FLOAT(), nullable=False, primary_key=True)
    Bucket = sa.Column(mysql.VARCHAR(length=255), nullable=False)
    Filename = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    ObsID = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=False)
    Detector = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=False)
    MonitorNeed = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)
    MonitorRun = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)
    MonitorFail = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)
    LogsPath = sa.Column(mysql.VARCHAR(length=255), nullable=True)
    UUID = sa.Column(mysql.VARCHAR(length=255), nullable=False)

class AstrometryOffsetTable(Base):
    __tablename__ = 'AstroOffset'
    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
        'mysql_default_charset': 'utf8mb4',
        'mysql_engine': 'InnoDB'
    }
    ID = sa.Column(mysql.INTEGER(), autoincrement=True, nullable=False, primary_key=True)
    Bucket = sa.Column(mysql.VARCHAR(length=255), nullable=True)
    File = sa.Column(mysql.VARCHAR(length=255), nullable=True)
    Offset = sa.Column(mysql.FLOAT(), nullable=True)
    NumSources = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=True)

class AstrometryResultsTable(Base):
    __tablename__ = 'AstrometryResults'
    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
        'mysql_default_charset': 'utf8mb4',
        'mysql_engine': 'InnoDB'
    }
    Bucket = sa.Column(mysql.VARCHAR(length=255), nullable=False)
    File = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    Offset = sa.Column(mysql.FLOAT(), nullable=False)
    NumSources = sa.Column(mysql.INTEGER(), autoincrement=False, nullable=False)
    Time = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    FileType = sa.Column(mysql.VARCHAR(length=255), nullable=False)

class Noise1FResultsTable(Base):
    __tablename__ = '1FResults'
    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
        'mysql_default_charset': 'utf8mb4',
        'mysql_engine': 'InnoDB'
    }
    Bucket = sa.Column(mysql.VARCHAR(length=255), nullable=False)
    File = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    SuccessfulCorrection = sa.Column(mysql.TINYINT(display_width=1), autoincrement=False, nullable=False)
    Time = sa.Column(mysql.VARCHAR(length=255), nullable=False, primary_key=True)
    FileType = sa.Column(mysql.VARCHAR(length=255), nullable=False)