#!/usr/bin/python3
# -*- coding: utf-8 -*-

from flask import current_app, g
from datetime import datetime,date
import pymysql
import hashlib

'''
from enum import Enum
class VioType(Enum):
    Generic = 1 #001
    Absence = 2 #010
    Sleep = 4   #100
VioTypeMap = [{VioGeneric:'Generic'},{VioAbsence:'Absence'},{VioSleep:'Sleep'}]
'''

'''
from DBUtils.PooledDB import PooledDB
class hstt_conn(PooledDedicatedDBConnection):
    def __enter__(self):
        print "In __enter__()"
              return "test_with"
    def __exit__(self, type, value, trace):
        print "In __exit__()"

def get_db():
    if not hasattr(g, 'hs_db_pool'):
        print('initial pooldb!')
        pool = PooledDB(creator=pymysql,mincached=2,maxcached=5,maxshared=3,maxconnections=6,blocking=True,
                        host='localhost',port=3306,user='vw',password='letmein',db='hs_timetable', charset='utf8')
        g.hs_tt_db = pool
    else:
        pool = g.hs_db_pool

    return pool.connection(
'''

# http://www.cnblogs.com/zhaohuhu/p/9218075.html

VioAbsence = 1
VioLate = 2
VioGeneric = 4
VioTypeMap = {VioAbsence:'Absence',VioLate:'Late',VioGeneric:'Violation'}

def get_weekofday():
    return datetime.now().weekday()+1 #need to consider the timezone

def get_today():
    #return date(2019,2,18)
    return datetime.today().date() #need to consider the timezone

# count the index of week in one semester, also return if in vacations
def count_week(today,start,end,vacations):
    day_diff = 0
    day_vac = 0
    is_vacation = False
    if len(vacations) == 0: # no vacation
        day_diff = (today-start).days
    else:
        for vac in vacations:
            vstart =vac[0]
            vend =vac[1]
            if(today-vstart).days < 0: # today before vacation
                day_diff = (today-start).days
                break
            elif(today-vend).days <= 0: # today in vacation
                day_diff = (vstart-start).days-1
                is_vacation = True
                break
            else: # today after vacation
                # semester ends with a vacation, so the loop will go on.
                day_vac += (vend-vstart).days+1

    week_index = (day_diff - day_vac)//7 + 1

    return week_index,is_vacation
    
    
def get_vioset_strfull(vio_value):
    vioset_desc = []
    if(vio_value & VioAbsence > 0):
        vioset_desc.append('Absence')
    if(vio_value & VioLate > 0):
        vioset_desc.append('Late')
    if(vio_value & VioGeneric > 0):
        vioset_desc.append('Violation')
    return ','.join(vioset_desc)

def get_vioset_str(vio_value):
    vioset_desc = []
    if(vio_value & VioAbsence > 0):
        vioset_desc.append('ABS')
    if(vio_value & VioLate > 0):
        vioset_desc.append('LAT')
    if(vio_value & VioGeneric > 0):
        vioset_desc.append('VIO')
    return ','.join(vioset_desc)

def connect_db():
    """Connects to the specific database."""
    #db = pymysql.connect(user='vw', password='****', database='hs_timetable', charset='utf8')
    db = pymysql.connect(**current_app.config['DATABASE'])
    #db.autocommit(1) 
    return db

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'hs_tt_db'):
        #print('connect db!')
        g.hs_tt_db = connect_db()
    return g.hs_tt_db

def do_hash(str):
    hashfun = hashlib.md5()
    hashfun.update(str.encode('utf-8'))
    return hashfun.hexdigest()
    
