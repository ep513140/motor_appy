import pytest
import mysql.connector
from make_mysql import waitingHook
from engine import RunEngine
from status import StatusAxis
from bluesky.plans import scan
from ophyd.status import MoveStatus, wait as status_wait
from ophyd.status import MoveStatus as MoveStatus
from ophyd.sim import SynAxis
from datetime import datetime
from ophyd.sim import SynGauss
from motor_plot import make_scatter, plot_motor, add_tbls, add_motors, unsuccess_line, unapproved_move, update_chart
import time
import unittest
import os

@pytest.fixture(scope='class')
def class_db(request):
        print("here")
        mydb = mysql.connector.connect(
        host=os.environ['MYSQL_HOST'],
        user=os.environ['MYSQL_USER'],
        passwd=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DB'],
        )
        cursor = mydb.cursor(buffered=True)
        
        motor = StatusAxis(name = 'testMotor')
        motor.prefix = 'prefix'
        det = SynGauss('det', motor, 'testMotor', center=0, Imax=1, sigma=1)
        det.kind = 'hinted'
        wh = waitingHook()
        mydb.commit()
        RE = RunEngine()
        RE.waiting_hook = wh
        RE(scan([], motor, 1, 3, 3))
        time.sleep(2)
        mydb.commit()
        request.cls.db =  mydb

def make_db(self):
        mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="ep513140",
        database="motordb",
        )
        cursor = mydb.cursor(buffered=True)
        cursor.execute("USE motordb")
        motor = StatusAxis(name = 'testMotor')
        motor.prefix = 'prefix'
        det = SynGauss('det', motor, 'testMotor', center=0, Imax=1, sigma=1)
        det.kind = 'hinted'
        wh = waitingHook()
        mydb.commit()
        RE = RunEngine()
        RE.waiting_hook = wh
        RE(scan([], motor, 1, 3, 3))
        time.sleep(2)
        mydb.commit()
        return mydb


@pytest.fixture(scope = 'class')
def class_plot(request):
        start_time = datetime.today()
        get_motor = plot_motor('testMotor', start_time, start_time, 0, 0, False)
        request.cls.plot = get_motor


    #checks if data from scan was added to table via data_entry method
@pytest.mark.usefixtures('class_db', 'class_plot')
class test_motor(unittest.TestCase):
    @pytest.mark.run(order=1)
    def test_data_length(self):
        print("data length failure, incorrect amount of MoveStatuses returned")
        cursor = self.db.cursor()
        cursor.execute("SELECT finish_pos FROM testMotor")
        num = cursor.fetchall()
        assert len(num) == 3

    #checks position values rounded with one decimal
    @pytest.mark.run(order=2)
    def test_round(self):
        print("round pos failure, numbers rounded incorrectly")
        cursor = self.db.cursor()
        cursor.execute("SELECT finish_pos FROM testMotor")
        num = cursor.fetchall()
        assert len(num[0][0]) == 3

    #checks if get_data method retrieves all columns of data correctly
    @pytest.mark.run(order=3)
    def test_check_cols(self):
        print("check cols failure, datatable wrong size")
        start_time = datetime.today().strftime('%Y-%m-%d')
        stop_time = datetime.today().strftime('%Y-%m-%d')
        wh = waitingHook()
        df = waitingHook.get_data(wh, 'testMotor', start_time, stop_time)
        assert df.shape == (3, 8)

    #tests that UI plot catches an unsuccessful event
    @pytest.mark.run(order=4)
    def test_unsuccess(self):
        print("test unsuccess failure, unsuccessful event not found")
        cursor = self.db.cursor()
        cursor.execute("USE motor_movements")
        cursor.execute("UPDATE testmotor SET success='False' WHERE target=3.0")
        cursor.execute("UPDATE testmotor SET finish_pos=2.0 WHERE target=3.0")
        self.db.commit()
        time.sleep(0.01)
        get_motor = plot_motor('testMotor', datetime.today(), datetime.today(), 0, 0, False)
        assert get_motor[0][1].name == 'Unsuccessful Event'

    #tests that UI plot catches and unapproved move
    @pytest.mark.run(order=5)
    def test_unapproved(self):
        print("test_unapproved failure, unapproved move not found")
        cursor = self.db.cursor()
        cursor.execute("USE motor_movements")
        cursor.execute("UPDATE testmotor SET start_pos=2.0 WHERE start_pos=1.0")
        self.db.commit()
        time.sleep(0.01)
        get_motor = plot_motor('testMotor', datetime.today(), datetime.today(), 0, 0, False)
        assert get_motor[0][2].name == 'Unapproved Move'

    #deletes datatable
    @pytest.mark.run(order=6)
    def test_delete_table(self):
        print("delete table failure, testMotor table was not deleted correctly")
        cursor = self.db.cursor()
        cursor.execute("DROP TABLE testmotor")
