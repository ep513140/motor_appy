import mysql.connector
import time
import datetime
import random
import threading
import time
from functools import partial
from ophyd.status import MoveStatus, wait as status_wait
from ophyd.status import MoveStatus as MoveStatus
from ophyd.sim import SynAxis
from bluesky import RunEngine
from bluesky.plans import scan
from bluesky.callbacks.best_effort import BestEffortCallback
from ophyd.sim import SynGauss
import os
from status import StatusAxis
import getpass
import pandas



class waitingHook():
    def __init__(self):
        mydb = mysql.connector.connect(
        host=os.environ['MYSQL_HOST'],
        user=os.environ['MYSQL_USER'],
        passwd=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DB'],
        )
        self.mydb = mydb

    def __call__(self, statuses):
        if statuses!=None:
            for stat in statuses:
                    if isinstance(stat, MoveStatus) and stat.pos.prefix!='':
                        time.sleep(0.01)
                        self.motorName = stat.pos.name
                        self.create_table(str(stat.pos.name), self.mydb)
                        user = getpass.getuser()
                        stat.add_callback(partial(self.data_entry, status = stat, user = user, prefix = stat.pos.prefix))

    def data_entry(self, status, user, prefix):
        mycursor = self.mydb.cursor()
        start = status.start_ts
        finish = status.finish_ts
        start_ts = str(datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S'))
        finish_ts = str(datetime.datetime.fromtimestamp(finish).strftime('%Y-%m-%d %H:%M:%S'))
        start_pos = round(status.start_pos,1)
        finish_pos = round(status.finish_pos,1)
        target = round(status.target,1)
        user = str(user)
        temp = str(status.success)
        prefix = str(prefix)
        motorName = self.motorName
        if temp==0:
            success = "False"
        else:
            success = "True"
        mycursor.execute("INSERT INTO "+motorName+" (start_ts, finish_ts, start_pos, finish_pos, target, success, user, prefix) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
        (start_ts, finish_ts, start_pos, finish_pos, target, success, user, prefix))
        self.mydb.commit()



    def create_table(self, motorName, mydb):
        mycursor = mydb.cursor()
        mycursor.execute("SHOW TABLES")
        tbls = mycursor.fetchall()
        mycursor.execute("CREATE TABLE IF NOT EXISTS "+motorName+" (start_ts VARCHAR(19) NOT NULL, finish_ts VARCHAR(19) NOT NULL, start_pos VARCHAR(10) NOT NULL, finish_pos VARCHAR(10) NOT NULL, target VARCHAR(10) NOT NULL, success VARCHAR(5) NOT NULL, user VARCHAR(15) NOT NULL, prefix VARCHAR(30) NOT NULL)")
        mydb.commit()
        mycursor.close()

    def get_data(self, motor, start_time, stop_time):
        mycursor = self.mydb.cursor()

        query = "SELECT start_ts, finish_ts, start_pos, finish_pos, target, success, user, prefix FROM "+motor+" WHERE STR_TO_DATE(start_ts, '%Y-%m-%d') >= '"+start_time+"' AND STR_TO_DATE(start_ts, '%Y-%m-%d') <= '"+stop_time+"'"
        df = pandas.read_sql_query(query, self.mydb)

        self.mydb.commit()
        mycursor.close()
        return df

    def get_tables(self):
        mycursor = self.mydb.cursor()
        mycursor.execute("SELECT table_name FROM information_schema.tables where table_schema='motor_movements'");
        tables = mycursor.fetchall()
        return tables
