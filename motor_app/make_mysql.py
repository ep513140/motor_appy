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

from status import StatusAxis
import getpass
import pandas



class waitingHook():
    def __init__(self, motorName):
        mydb = mysql.connector.connect(
        host="psdb-dev",
        user="ella",
        passwd="pcds",
        database="motor_movements",
        )
        cursor = mydb.cursor()
        self.create_table(motorName, mydb)
        self.motorName = motorName
        self.mydb = mydb

    def __call__(self, statuses):
        if statuses!=None:
            for stat in statuses:
                    if isinstance(stat, MoveStatus):
                        user = getpass.getuser()
                        stat.add_callback(partial(self.data_entry, status = stat, user = user))

    def data_entry(self, status, user):
        mycursor = self.mydb.cursor()
        start = status.start_ts
        finish = status.finish_ts
        start_ts = str(datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S'))
        finish_ts = str(datetime.datetime.fromtimestamp(finish).strftime('%Y-%m-%d %H:%M:%S'))
        start_pos = int(round(status.start_pos))
        finish_pos = int(round(status.finish_pos))
        target = int(round(status.target))
        user = str(user)
        temp = str(status.success)
        motorName = self.motorName
        if temp==0:
            success = "False"
        else:
            success = "True"
        mycursor.execute("INSERT INTO "+motorName+" (start_ts, finish_ts, start_pos, finish_pos, target, success, user) VALUES(%s, %s, %s, %s, %s, %s, %s)",
        (start_ts, finish_ts, start_pos, finish_pos, target, success, user))
        #insert_tuple = (start_ts, finish_ts, start_pos, finish_pos, target, success, user)
        #sql_insert_query = "INSERT INTO "+motorName+" (start_ts, finish_ts, start_pos, finish_pos, target, success, user) VALUES(%s, %s, %s, %s, %s, %s, %s)",
        #result  = mycursor.execute(sql_insert_query, insert_tuple)
        self.mydb.commit()



    def create_table(self, motorName, mydb):
        mycursor = mydb.cursor()

        #mycursor.execute(SET @table_name = motorName)
        #table_name = motorName
        mycursor.execute("CREATE TABLE IF NOT EXISTS " +motorName+" (start_ts VARCHAR(19) NOT NULL, finish_ts VARCHAR(19) NOT NULL, start_pos VARCHAR(10) NOT NULL, finish_pos VARCHAR(10) NOT NULL, target VARCHAR(10) NOT NULL, success VARCHAR(5) NOT NULL, user VARCHAR(15) NOT NULL)")
        mydb.commit()


    def get_data(self, motor, start_time, stop_time):
        mycursor = self.mydb.cursor()

        query = "SELECT start_ts, finish_ts, CAST(start_pos AS UNSIGNED), CAST(finish_pos AS UNSIGNED), CAST(target AS UNSIGNED), success, user FROM "+motor+" WHERE STR_TO_DATE(start_ts, '%Y-%m-%d') >= '"+start_time+"' AND STR_TO_DATE(start_ts, '%Y-%m-%d') <= '"+stop_time+"'"
        df = pandas.read_sql_query(query, self.mydb)

        self.mydb.commit()
        mycursor.close()
        return df
