#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    Admin
    ~~~~~~

    A microblog example application written as Flask tutorial with

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from flask import Blueprint, request, session, redirect, url_for, abort, \
     render_template, flash
from functools import wraps

import sys
sys.path.append('views/')
from common import connect_db, get_db, do_hash
from math import ceil

# create our blueprint :)
admin = Blueprint('admin', __name__)

WeekDay =  { 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat', 7:'Sun' }
DaySlot = { 1:'1st', 2:'2nd',3:'3rd', 4:'4th', 5:'5th', 6:'6th', 7:'7th' }

PageSizeTimeTable = 20

def check_login(func):
    @wraps(func)
    def cl_wrapper(*args,**kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin.login'))
        return func(*args,**kwargs)
    return cl_wrapper

@admin.route('/')
@admin.route('/ttshow', methods=['GET', 'POST'])
@check_login
def show_timetable():
    # request.form.get("key") post/ request.args.get("key") get/ request.values.get("key") all para
    db = get_db()
    with db.cursor() as cursor:
        sql_str_arr = []
        sql_count_arr = []
        sql_str_arr.append('select m.id,m.day,m.slot,c.sname,t.name,cr.name from timetable as m,teachers as t \
        ,courses as c,classrooms as cr where m.t_id = t.id and m.c_id = c.id and m.cr_id = cr.id')
        sql_count_arr.append('select count(m.id) from timetable as m,teachers as t \
        ,courses as c,classrooms as cr where m.t_id = t.id and m.c_id = c.id and m.cr_id = cr.id')

        if request.method == 'POST':
            sea_day = request.form.get('SeaDay', type=int, default=0)
            sea_slot = request.form.get('SeaSlot', type=int, default=0)
            sea_cid = request.form.get('SeaCourse', type=int, default=0)
            sea_tid = request.form.get('SeaTeacher', type=int, default=0)
            sea_crid = request.form.get('SeaClassroom', type=int, default=0)        
            if sea_day>0 :
                sql_str_arr.append(' and m.day=%d'%sea_day)
                sql_count_arr.append(' and m.day=%d'%sea_day)
            if sea_slot>0:
                sql_str_arr.append(' and m.slot=%d'%sea_slot )
                sql_count_arr.append(' and m.slot=%d'%sea_slot )
            if sea_cid>0:
                sql_str_arr.append(' and c.id=%d'%sea_cid )
                sql_count_arr.append(' and c.id=%d'%sea_cid )
            if sea_tid>0:
                sql_str_arr.append(' and t.id=%d'%sea_tid )
                sql_count_arr.append(' and t.id=%d'%sea_tid )
            if sea_crid>0:
                sql_str_arr.append(' and cr.id=%d'%sea_crid )
                sql_count_arr.append(' and cr.id=%d'%sea_crid )
        else:
            sea_day = sea_slot = sea_cid = sea_tid = sea_crid = 0

        # count page and select section
        count_sql = ''.join(sql_count_arr)
        cursor.execute(count_sql)
        ret_count = cursor.fetchone()
        total_count = int(ret_count[0])

        #page_index_para = request.cookies.get('PageIndex')
        page_index = request.form.get('PageIndex', type=int, default=0)
        if page_index == 0 and total_count > 0:
            page_index = 1

        sel_begin = 0
        page_count = ceil(total_count/PageSizeTimeTable)
        if page_index > page_count:
            page_index = page_count
            sel_begin = (page_index-1)*PageSizeTimeTable
        elif page_index>0:
            sel_begin = (page_index-1)*PageSizeTimeTable 

        entries = []
        if total_count > 0:
            # control select section
            sql_str_arr.append((' order by m.id desc limit %d,%d')%(sel_begin,PageSizeTimeTable))
            sel_sql = ''.join(sql_str_arr)
            cursor.execute(sel_sql)
            entries = cursor.fetchall()

        sea_par = dict(S_day=sea_day,S_slot=sea_slot,S_cid=sea_cid,S_tid=sea_tid,S_crid=sea_crid)
        if(not session.get('tbl_opt_map')):
            #print('Loading from db for opt map...')
            cursor.execute('select id,name from classrooms order by name')
            cr_tbl = cursor.fetchall()
            cursor.execute('select id,sname from courses order by sname')
            co_tbl = cursor.fetchall()
            cursor.execute('select id,name from teachers where id<200')
            te_tbl = cursor.fetchall()
            session['tbl_opt_map'] = dict(CR=cr_tbl,CO=co_tbl,TE=te_tbl)

    return render_template('show_timetable.html',entries=entries,
                           page_index=page_index,page_count=page_count,
                           sel_day=WeekDay,sel_slot=DaySlot,S_par=sea_par)


@admin.route('/ttadd', methods=['POST'])
@check_login
def add_timetable():
    db = get_db()
    with db.cursor() as cursor:
        add_day = request.form.get('WeekDay', type=int,default=0)
        add_slot = request.form.get('DaySlot', type=int,default=0)
        add_slen = request.form.get('SlotLen', type=int, default=1)
        add_tid = request.form.get('OptTeacher', type=int,default=0)
        add_cid= request.form.get('OptCourse', type=int,default=0)
        add_crid = request.form.get('OptClassroom',type=int,default=0)
        session['add_par'] = dict(A_day=add_day,A_slot=add_slot,A_slen=add_slen,
                                  A_tid=add_tid,A_cid=add_cid,A_crid=add_crid)
        for n in range(0,add_slen):
            cursor.execute('insert into timetable (day,slot,t_id,c_id,cr_id) values (%s,%s,%s,%s,%s)',
                           (add_day, add_slot+n, add_tid, add_cid, add_crid))
        db.commit()
    return redirect(url_for('admin.show_timetable'))

@admin.route('/ttdelete', methods=['POST'])
@check_login
def delete_timetable():
    ttid = request.form.getlist('TTID')
    if(not ttid):
        return redirect(url_for('admin.show_timetable'))
    db = get_db()
    with db.cursor() as cursor:
        id_list = ','.join(ttid)
        del_str = 'delete from timetable where id in (%s)'%id_list
        cursor.execute(del_str)
        db.commit()
    return redirect(url_for('admin.show_timetable'))

    
@admin.route('/ttpurge', methods=['GET','POST'])
@check_login
def purge_timetable():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('truncate timetable')
        db.commit()
    return redirect(url_for('admin.show_timetable'))
    
@admin.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute('select authority,status from users where username=%s and password=%s limit 1',
                           (request.form['username'],do_hash(request.form['password'])))
            
            one_user = cursor.fetchone()
            if(one_user == None):
                error = 'Wrong username or password!'
            elif(one_user[1]!=0):
                error = 'User suspend! Contact Administrator.'
            elif(one_user[0]>1):
                error = 'Insufficient privilege! Contact Administrator'
            else:
                session['logged_in'] = True
                flash('You were logged in')
                return redirect(url_for('admin.show_timetable'))
    return render_template('login.html', error=error)


@admin.route('/logout')
def logout():    
    session.pop('logged_in', None)
    session.pop('tbl_opt_map',None)
    session.pop('add_par',None)
    flash('You were logged out')
    return redirect(url_for('admin.login'))
