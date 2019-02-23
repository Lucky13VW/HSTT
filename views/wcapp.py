#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    For WeChat backend server
    ~~~~~~
    Based on flask
    :copyright: (c) 2018 by Victor Wu.
"""

from flask import Blueprint, request, session, g, current_app, jsonify
from functools import wraps
import json
import urllib

import sys
sys.path.append('views/')
from common import * 

# create our blueprint :)
wcapp = Blueprint('wcapp', __name__)

'''
def check_login(func):
    @wraps(func)
    def cl_wrapper(*args,**kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin.login'))
        return func(*args,**kwargs)
    return cl_wrapper
'''

'''
@wcapp.route('/wcsignup',methods=['GET','POST'])
def wc_signup():
    reg_info = json.loads(request.data)
    su_user = reg_info['su_user']
    su_pass = reg_info['su_pass']
    error = None
    status = 0
        
    db = get_db()
    with db.cursor() as cursor:
        # if it exists
        cursor.execute('select username from users where username=%s limit 1',(su_user))
        record = cursor.fetchone()
        if not record:
            cursor.execute('select id from teachers where phone=%s limit 1',(su_user))
            record = cursor.fetchone()
            if not record:
                status = 2
                error = "SignUp failed! You are not a teacher!"
            else: # found from teacher table,permit it!
                tid = record[0]
                cursor.execute('insert into users (username,password,tid,authority,status) \
                values (%s,%s,%s,%s,%s,%s)',(su_user,do_hash(su_pass),tid,2,0))
                db.commit()
                status = 0
                error  = "SignUp Ok!"
        else:
            status = 1
            error = "User already xists!"
            
    return jsonify({'status':status,'error':error})
'''

ERR_SIGNUP_OK = 0
ERR_SIGNUP_MISMATCH = 1
ERR_SIGNUP_SUSPEND = 2
ERR_SIGNUP_OPENID = 4
ERR_SYS_NOT_AVAILABEL = 99

@wcapp.route('/wcsignup',methods=['GET','POST'])
def wc_signup():
    result = {}
    db = get_db()
    with db.cursor() as cursor:
        if request.method == 'GET': # initial load page
            cursor.execute('select id,name,type,phone from teachers where type<3 or type=9')
            records = cursor.fetchall()
            teachers = {}
            for id,name,type,phone in records:
                if(phone and len(phone)>0):
                    tphone = phone
                else:
                    tphone = ''
                teachers.update({id:[name,type,tphone]})
                
            result.update({'teachers':teachers})
        else: # sign up request
            input = json.loads(request.data)
            code = input['code']
            req_url = current_app.config['WC_URL_Login']+code
            error = ERR_SYS_NOT_AVAILABEL
            with urllib.request.urlopen(req_url) as req:
                res = req.read()
                #for key,value in req.getheaders():
                #    print('%s: %s' %(key,value))
                data = json.loads(res)
                openid = data.get('openid',None)
                if openid:
                    tid_para = input['t_id']
                    t_id = int(tid_para) if(tid_para) else 0

                    mode_flag = input['mode']
                    mode = int(mode_flag) if(mode_flag) else 0                    
                    if mode == 1: # for admin login to debug, can be any teacher
                        cursor.execute('select id from users where authority=1 and status=0 and openid=%s limit 1',openid)
                        user_auth = cursor.fetchone()
                        if user_auth:
                            uid = user_auth
                            cursor.execute('select id,type,name from teachers where id=%s limit 1',t_id)
                            one_user = cursor.fetchone()
                            if one_user:
                                tid,ttype,tname=one_user
                                result.update({'uid':uid,'tid':tid, 'ttype':ttype,'tname':tname})
                                error = ERR_SIGNUP_OK
                        else:
                            error = ERR_SIGNUP_SUSPEND #'User suspend! Contact Administrator.'
                    else:
                        need_login = True
                        # if it exists
                        cursor.execute('select t_id from users where openid=%s and authority<>1 limit 1',openid)
                        record = cursor.fetchone()
                        if not record: # new user, sign up
                            cursor.execute('insert into users(openid,t_id,authority,status) values (%s,%s,%s,%s)',(openid,t_id,2,0))
                            db.commit()
                        elif record[0] != t_id: # user exists but openid and t_id mismatches!
                            need_login = False
                            error = ERR_SIGNUP_MISMATCH

                        if need_login: # user exists or just created, sign in
                            cursor.execute('select u.status,u.id,u.t_id,t.type,t.name from users as u,teachers as t \
                                            where u.t_id=t.id and t.id=%s limit 1',t_id)
                            one_user = cursor.fetchone()
                            if one_user:
                                status,uid,tid,ttype,tname = one_user
                                if status == 0:
                                    result.update({'uid':uid,'tid':tid, 'ttype':ttype,'tname':tname})
                                    error = ERR_SIGNUP_OK
                                else: # user is suspended now
                                    error = ERR_SIGNUP_SUSPEND

                else: # fail to get openid
                    error = ERR_SIGNUP_OPENID 
                    
            result.update({'error':error})

    return jsonify(result)

@wcapp.route('/wclogin',methods=['POST'])
def wc_login():
    login_info = json.loads(request.data)
    mode_flag = login_info['mode']
    mode = int(mode_flag) if(mode_flag) else 0

    error = 0
    uid = 0
    tid = 0
    ttype = 0
    tname = 'Visitor'

    db = get_db()
    with db.cursor() as cursor:
        if mode==1:
            cursor.execute('select u.authority,u.status,u.id,u.t_id,t.type,t.name from users as u,teachers as t \
                           where u.t_id=t.id and username=%s and password=%s limit 1',
                           (login_info['user'],do_hash(login_info['pass'])))

            one_user = cursor.fetchone()
            if one_user is None:
                error = 1 #'Wrong username or password!'
            else:
                auth,status,uid,tid,ttype,tname = one_user
                if auth != 2:
                    error =  2 #'It\'s only for teachers!'
                elif status != 0:
                    error = 3 #'User suspend! Contact Administrator.'
            
        else:  # by default login by wechat
            code = login_info['code']
            req_url = current_app.config['WC_URL_Login']+code

            with urllib.request.urlopen(req_url) as req:
                res = req.read()
                #for key,value in req.getheaders():
                #    print('%s: %s' %(key,value))
                data = json.loads(res)
                openid = data.get('openid',None)
                #print(openid)
                if openid:
                    cursor.execute('select u.authority,u.status,u.id,u.t_id,t.type,t.name from users as u,teachers as t \
                                    where u.t_id=t.id and u.openid=%s limit 1',openid)
                    one_user = cursor.fetchone()
                    if one_user:
                        auth,status,uid,tid,ttype,tname = one_user
                        if auth != 2:
                            error =  2 #'It\'s only for teachers!'
                        elif status != 0:
                            error = 3 #'User suspend! Contact Administrator.'
                        else:
                            error = 9 # no user found, need to signup
                else:
                    error = 4 # fail to get openid

    return jsonify({'error': error,'uid':uid,'tid':tid, 'ttype':ttype,'tname':tname})

@wcapp.route('/wchome',methods=['POST'])
def wc_home():
    t_info = json.loads(request.data)
    t_id = t_info['tid']
    ttype_flag = t_info['ttype']
    t_type = int(ttype_flag) if (ttype_flag) else 1
    db = get_db()
    output = {}
    with db.cursor() as cursor:
        is_vacation = False
        today=[]
        week_index= 0
        se_id = 0
        day_today = get_today()

        cursor.execute('select s.id,s.start,s.end,v.start,v.end from semesters as s left join vacations as v \
                        on v.se_id=s.id where %s between s.start and s.end',day_today.isoformat())
        semesters = cursor.fetchall()
        if semesters:
            vacations = []
            for(id,ss,se,vs,ve) in semesters:
                se_id = id
                start = ss
                end = se
                if vs and ve:
                    vacations.append((vs,ve))

            week_index,is_vacation = count_week(today=day_today,start=start,end=end,vacations=vacations)

        if not is_vacation:
            if(t_type == 2): # form teacher, get attendlist for today
                cursor.execute('select a.id,a.vio_value,ae.s_name,ae.c_sname,ae.slot from attendance as a,attendext as ae \
                                where a.id = ae.a_id and to_days(a.tt_date)=to_days(%s) and ae.ft_id=%s',(day_today,t_id)) 
                attend_today = cursor.fetchall()
                ids=[]
                if(attend_today):
                    for(id,vio_value,s_name,c_name,slot) in attend_today:
                        vioset_str = get_vioset_str(vio_value)
                        one_rec='{0} Slot{1} {2}({3})'.format(s_name,slot,c_name,vioset_str)
                        today.append(one_rec)
                        ids.append(id)

                output.update({'id':ids})
               
            else: # normal teacher, get courses for today
                week_of_day =  get_weekofday()
                cursor.execute('select tt.slot,c.sname,cr.name from courses as c,classrooms as cr, timetable as tt \
                                where tt.c_id = c.id and tt.cr_id = cr.id and tt.t_id=%s and tt.day=%s order by tt.slot',(t_id,week_of_day))
                course_today = cursor.fetchall()
            
                if(course_today):

                    for(slot,c_name,cr_name) in course_today:
                        one_rec='Slot{0}: {1}@{2}'.format(slot,c_name,cr_name)
                        today.append(one_rec)

        output.update({'vacation':is_vacation,'today':today,'week':week_index,'seid':se_id})
            
    return jsonify(output)
            
@wcapp.route('/wcattendance',methods=['GET'])
def wc_attendance():
    step = request.values.get("step")
    step_flag = int(step) if step else 0

    t_id = request.values.get("tid")
    ret_data = {}
    db = get_db()
    with db.cursor() as cursor:
        if(step_flag == 0): # initial page load, load courses
            ttid = []
            ttcourse = []
            courseid = []
            week_of_day =  get_weekofday()
            cursor.execute('select tt.id,tt.slot,c.sname,cr.name,c.id from courses as c,classrooms as cr, timetable as tt \
                            where tt.c_id = c.id and tt.cr_id = cr.id and tt.t_id=%s and tt.day=%s order by tt.slot',(t_id,week_of_day))
            course_today = cursor.fetchall()
            if course_today:
                for (id,slot,name,cr,cid) in course_today:
                    ttid.append(id)
                    courseid.append(cid)
                    str_course = 'Slot{0}={1}@{2}'.format(slot,name,cr)
                    ttcourse.append(str_course)
                        
            ret_data = {'ttid':ttid,'ttcourse':ttcourse,'ttcid':courseid,'viomap':VioTypeMap}
            
        else: # course selected, load students
            c_id = request.values.get("cid")
            sid = []
            sname=[]
            cursor.execute('select s.id,s.name,s.eng_name from students as s,enrollment as e \
                    where e.s_id = s.id and e.t_id = %s and e.c_id = %s',(t_id,c_id))
            students = cursor.fetchall()
            if students:
                for(id,name,ename) in students:
                    sid.append(id)
                    str_name = '{0}({1})'.format(name,ename)
                    sname.append(str_name)
            ret_data = {'sid':sid,'sname':sname}

    return  jsonify(ret_data)

@wcapp.route('/wcsnitch',methods=['POST'])
def wc_snitch():
    input = json.loads(request.data)
    tt_id = input['ttid']
    t_id = input['tid']
    s_id = input['sid']
    se_id = input['seid']
    week = input['week']
    vio_value = input['viovalue']
    vio_desc = input['viodesc']
    tt_date = get_today()
    status = 0
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('select id from attendance where tt_id=%s and s_id=%s and tt_date=%s limit 1',
                       (tt_id,s_id,tt_date))
        tt_record = cursor.fetchone()
        try:
            if(tt_record): # already exist, update the vio_value and vio_desc
                tbl_id = tt_record
                cursor.execute('update attendance set vio_value=%s, vio_desc=%s where id=%s',(vio_value,vio_desc,tbl_id))
                status = 2
            else: # new, insert it
                cursor.execute('insert into attendance(tt_id,s_id,t_id,vio_value,vio_desc,tt_date,se_id,week) values(%s,%s,%s,%s,%s,%s,%s,%s)',
                               (tt_id,s_id,t_id,vio_value,vio_desc,tt_date,se_id,week))
                status = 1
                
            db.commit()
        except Exception as e:
            status = -1
            repr(e)
            print('wc_snitch fails rollback!')
            db.rollback() 
        
    return jsonify({'status':status})

@wcapp.route('/wcattendrecord',methods=['GET'])
def wc_attendrecord():
    aid_para = request.values.get("aid")
    a_id = int(aid_para) if aid_para else 0
    output = {}
    db = get_db()
    with db.cursor() as cursor:
        if(a_id >0): 
            action = int(request.values.get("action"))
            if(action == 0): # for attend detail
                cursor.execute('select a.vio_value,a.vio_desc,a.tt_date,ae.s_name,ae.s_ename,ae.c_sname,ae.cr_name,ae.t_name,ae.ft_name,ae.slot,a.week \
                                from attendance as a,attendext as ae where a.id=ae.a_id and a.id=%s limit 1',a_id)
                att_detail = cursor.fetchone()
                if(att_detail):
                    vio_value,vio_desc,tt_date,s_name,s_ename,c_sname,cr_name,t_name,ft_name,slot,week = att_detail
                    if(len(s_ename)>0):
                        s_mixname = '{0}({1})'.format(s_name,s_ename)
                    else:
                        s_mixname = '{0}'.format(s_name)
                    tt_date_str = '{0}-{1}-{2}'.format(tt_date.year,tt_date.month,tt_date.day)
                    vio_setstr = get_vioset_strfull(vio_value)
                    output = {'tt_date':tt_date_str,'s_name':s_mixname,'vio_setstr':vio_setstr,'vio_desc':vio_desc,
                              'c_name':c_sname,'cr_name':cr_name,'t_name':t_name,'ft_name':ft_name,'slot':slot,'week':week}
                    
            else: # for attend withdraw
                status = 0
                try:
                    cursor.execute('delete from attendance where id = %s',a_id)
                    db.commit()
                except Exception as e:
                    status = -1
                    repr(e)
                    print('attendwithdraw fails rollback!')
                    db.rollback()

                output = {"status":status}
                
        else: # for attend list
            week = request.values.get("week")
            t_id = request.values.get("tid")
            t_type = int(request.values.get("ttype"))
            sea_sel = ('select a.id,a.vio_value,a.tt_date,ae.s_name,ae.s_ename,ae.c_sname,ae.slot from attendance as a,attendext as ae \
                        where a.id = ae.a_id and a.week=%s and '%week)
            sea_con = ''
            if t_type == 2: # form teacher, list students under him/her
                sea_con = ('ae.ft_id = %s'%t_id)            
            else: # teaching teacher, list students reported by him/her
                sea_con = ('a.t_id = %s'%t_id)

            sea_sql = '{0} {1} order by a.id desc'.format(sea_sel,sea_con)
            cursor.execute(sea_sql)
            tbl_attend = cursor.fetchall()
            att_text = []
            att_id = []
            cur_year = get_today().year

            for(id,vio_value,date,s_name,s_ename,c_sname,slot) in tbl_attend:
                vioset_str = get_vioset_str(vio_value)
                stu_name = ''
                if t_type == 1: # foreign teacher, show english name
                    stu_name = s_ename
                else:
                    stu_name = s_name
                if date.year == cur_year:
                    str_date = '{0}-{1}'.format(date.month,date.day)
                else:
                    str_date = date
                att_str = '{0} {1} Slot{2} {3}({4})'.format(str_date,stu_name,slot,c_sname,vioset_str)
                att_id.append(id)
                att_text.append(att_str)

            output={'att_text':att_text,'att_id':att_id}
    return jsonify(output)    

@wcapp.route('/wcevalweekly',methods=['GET'])
def wc_evalweekly():
    cid_para = request.values.get("cid")
    c_id = int(cid_para) if cid_para else 0
    t_id = request.values.get("tid")
    ttype_para = request.values.get("ttype")
    t_type = int(ttype_para) if ttype_para else 0
    output = {}
    db = get_db()
    with db.cursor() as cursor:
        if(c_id>0): # load students by seid,week,cid,tid
            se_id = request.values.get("seid")
            week = request.values.get("week")
            cursor.execute('select s.id,s.name,s.eng_name,e.academic,e.attitude,e.progress,e.comment,e.id from students as s,evalweekly as e \
                            where s.id=e.s_id and e.c_id=%s and e.t_id=%s and e.se_id=%s and e.week=%s',(c_id,t_id,se_id,week))
            evalweek = cursor.fetchall()
            is_new = True
            s_data=[]
            if evalweek:
                is_new = False
                for (sid,sname,sename,e_a,e_t,e_p,e_c,e_id) in evalweek:
                    s_one=[]
                    s_one.append(sid)
                    if t_type == 1: # english name
                        s_one.append(sename)
                    else:
                        s_one.append(sname)
                    s_one.append(e_a)
                    s_one.append(e_t)
                    s_one.append(e_p)
                    s_one.append(e_c)
                    s_one.append(e_id)
                    s_data.append(s_one)
                
            else: # no evalweekly currently
                cursor.execute('select e.s_id,s.name,s.eng_name from students as s,enrollment as e \
                                where e.s_id=s.id and e.c_id=%s and e.t_id=%s',(c_id,t_id))
                students = cursor.fetchall()
                if students:
                    for(sid,sname,sename) in students:
                        s_one = []
                        s_one.append(sid)
                        if t_type == 1: # english name
                            s_one.append(sename)
                        else:
                            s_one.append(sname)                        
                        s_data.append(s_one)
       
            output = {'sdata':s_data,'isnew':is_new}
            
        else: # load courses from tid
            cursor.execute('select c.id,c.sname from courses as c,timetable as tt \
                            where tt.c_id=c.id and tt.t_id=%s group by c.id;',t_id)
            
            courses = cursor.fetchall()
            arr_cid = []
            arr_cname=[]
            if courses:
                for(cid,cname) in courses:
                    arr_cid.append(cid)
                    arr_cname.append(cname)
            output={'cid':arr_cid,'cname':arr_cname}

    return jsonify(output)

@wcapp.route('/wcevalsubmit',methods=['POST'])
def wc_evalsubmit():
    eval_info = json.loads(request.data)
    se_id = eval_info['seid']
    week = eval_info['week']
    c_id = eval_info['cid']
    t_id = eval_info['tid']
    is_new = eval_info['isnew']
    s_data = eval_info['sdata']
    output = {}
    db = get_db()
    with db.cursor() as cursor:
        COL_SID= 0
        COL_SA = 1
        COL_ST = 2
        COL_SP = 3
        COL_SC = 4
        COL_EID= 5
        s_total = len(s_data)
        bulk_sql = []
        status = 0
        if is_new:
            status = 1
            bulk_sql.append('insert into evalweekly(se_id,week,c_id,t_id,s_id,academic,attitude,progress,comment) values')
            for index in range(s_total):
                values = '({0},{1},{2},{3},{4},{5},{6},{7},\'{8}\')'.format(se_id,week,c_id,t_id,s_data[index][COL_SID],s_data[index][COL_SA],
                                                                            s_data[index][COL_ST],s_data[index][COL_SP],s_data[index][COL_SC])
                bulk_sql.append(values)
                if index != s_total-1:
                    bulk_sql.append(',')
                
        else:
            #  update evalweekly set academic = case id when 1 then 3 when 2 then 4 end, attitude = case id when 1 then 1 when 2 then 2 end where id in (1,2);
            status = 2
            bulk_sql.append('update evalweekly set academic = case id ')
            for index in range(s_total):
                values = 'when {0} then {1} '.format(s_data[index][COL_EID],s_data[index][COL_SA])
                bulk_sql.append(values)

            bulk_sql.append('end, attitude = case id ')
            for index in range(s_total):
                values = 'when {0} then {1} '.format(s_data[index][COL_EID],s_data[index][COL_ST])
                bulk_sql.append(values)
                    
            bulk_sql.append('end, progress = case id ')
            for index in range(s_total):
                values = 'when {0} then {1} '.format(s_data[index][COL_EID],s_data[index][COL_SP])
                bulk_sql.append(values)

            bulk_sql.append('end, comment = case id ')
            for index in range(s_total):
                values = 'when {0} then \'{1}\' '.format(s_data[index][COL_EID],s_data[index][COL_SC])
                bulk_sql.append(values)

            bulk_sql.append('end where id in (')
            for index in range(s_total):
                if index == s_total-1:
                    values = '{0}{1}'.format(s_data[index][COL_EID],')')
                else:
                    values = '{0}{1}'.format(s_data[index][COL_EID],',')
                bulk_sql.append(values)
                    
        try:
            cursor.execute(''.join(bulk_sql))
            db.commit()
        except Exception as e:
            status = -1
            repr(e)
            print('wc_evalsubmit fails rollback!')
            db.rollback()
            
    output={'status':status}
    return jsonify(output)

@wcapp.route('/wcreportweekly',methods=['GET'])
def wc_reportweekly():
    week_para = request.values.get('week')
    week = int(week_para) if week_para else 0

    t_id = request.values.get('tid')
    t_type = int(request.values.get('ttype'))
    
    output = {}
    db = get_db()
    with db.cursor() as cursor:
        if(week == 0): # first time load courses/classes
            ccid=[]
            ccname=[]
            if(t_type == 2): # form teacher, load classes
                load_cc = 'select id,name from classes where ft_id={0}'.format(t_id)
            else: # normal teacher, load courses
                load_cc = 'select c.id,c.sname from courses as c,timetable as tt \
                            where tt.c_id = c.id and tt.t_id = {0} group by c.id;'.format(t_id)
            cursor.execute(load_cc)
            cc = cursor.fetchall()
            if cc:
                for (id,name) in cc:
                    ccid.append(id)
                    ccname.append(name)
            output={'ccid':ccid,'ccname':ccname}
            
        else: # load students by seid,week,tid,cid/clid
            se_id = request.values.get('seid')
            cc_id = request.values.get('ccid') # classid or courseid
            if(t_type == 2): # form teacher, load students under classes
                load_s = 'select s.id,s.name,s.eng_name,rw.absence,rw.sleep,rw.violation,rw.a_total,rw.a_count,rw.t_total,rw.t_count,rw.p_total,rw.p_count \
                          from students as s,reportweekly as rw,classes as cl where s.cl_id=cl.id and s.id=rw.s_id and \
                          cl.ft_id = {0} and cl.id={1} and rw.se_id={2} and rw.week={3}'.format(t_id,cc_id,se_id,week)
            else: # normal teacher, load students by course
                load_s = 'select s.id,s.name,s.eng_name,rw.absence,rw.sleep,rw.violation,rw.a_total,rw.a_count,rw.t_total,rw.t_count,rw.p_total,rw.p_count \
                          from students as s,reportweekly as rw, enrollment as e where s.id=rw.s_id and s.id=e.s_id and \
                          e.t_id = {0} and e.c_id={1} and rw.se_id={2} and rw.week={3}'.format(t_id,cc_id,se_id,week)                

            cursor.execute(load_s)
            students = cursor.fetchall()
            sdata=[]
            if students:
                for(id,name,e_name,abs,lat,vio,a_total,a_count,t_total,t_count,p_total,p_count) in students:
                    one_data = []
                    one_data.append(id)
                    if t_type == 1:
                        one_data.append(e_name)
                    else:
                        one_data.append(name)
                    a_val = 0 if a_count == 0 else round(a_total/a_count,1)
                    one_data.append(a_val)
                    t_val = 0 if t_count == 0 else round(t_total/t_count,1)
                    one_data.append(t_val)
                    p_val = 0 if p_count == 0 else round(p_total/p_count,1)
                    one_data.append(p_val)
                    one_data.append(abs)
                    one_data.append(lat)
                    one_data.append(vio)
                    sdata.append(one_data)

            output = {'sdata':sdata}

    return jsonify(output)

@wcapp.route('/wcreportdetail',methods=['GET'])
def wc_reportdetail():

    sid_para = request.values.get('sid')
    nosel_para = request.values.get('nosel')
    
    s_id = int(sid_para) if sid_para else 0    
    no_sel = int(nosel_para) if nosel_para else 0
    
    output = {}
    db = get_db()
    with db.cursor() as cursor:
        if s_id > 0: # load report detail by s_id
            se_id = request.values.get('se_id')
            week = int(request.values.get('week'))

            # load evaluation
            c_data = []
            if week>0: # in one week
                cursor.execute('select c.sname,e.academic,e.attitude,e.progress,e.comment from evalweekly as e,courses as c \
                                where c.id=e.c_id and e.s_id=%s and e.se_id=%s and e.week=%s',(s_id,se_id,week))

                c_report = cursor.fetchall()
                if c_report:
                    for(cname,s_a,s_t,s_p,s_c) in c_report:
                        one_data=[]
                        one_data.append(cname)
                        one_data.append(s_a)
                        one_data.append(s_t)
                        one_data.append(s_p)
                        one_data.append(s_c)
                        c_data.append(one_data)
            else: # all weeks, in one semester
                cursor.execute('select c.sname,sum(e.academic),sum(e.attitude),sum(e.progress),count(e.id) \
                                from evalweekly as e,courses as c where c.id=e.c_id and e.s_id=%s and e.se_id=%s group by c.id',(s_id,se_id))

                c_report = cursor.fetchall()
                if c_report:
                    for(cname,s_a,s_t,s_p,count) in c_report:
                        one_data=[]
                        one_data.append(cname)
                        a_avg = 0 if count == 0 else round(s_a/count,1)
                        one_data.append(str(a_avg))
                        t_avg = 0 if count == 0 else round(s_t/count,1)                        
                        one_data.append(str(t_avg))
                        p_avg = 0 if count == 0 else round(s_p/count,1)                        
                        one_data.append(str(p_avg))
                        c_data.append(one_data)

            output.update({'cdata':c_data})

            # load attendance
            a_data={}
            if week>0: # in one week
                cursor.execute('select absence,sleep,violation from reportweekly \
                                where s_id=%s and se_id=%s and week=%s limit 1',(s_id,se_id,week))
            else: # in one semester
                cursor.execute('select sum(absence),sum(sleep),sum(violation) from reportweekly \
                                where s_id=%s and se_id=%s group by se_id limit 1',(s_id,se_id))
                
            a_report = cursor.fetchone()
            abs= lat = vio = 0
            if a_report:
                abs,lat,vio = a_report
            a_data={'abs':str(abs),'lat':str(lat),'vio':str(vio)}
            output.update({'adata':a_data})

            r_data=[]
            rdata_sql = 'select a.id,a.tt_date,ae.c_sname,ae.t_name,a.vio_value from attendance as a,attendext as ae \
                         where a.id=ae.a_id and a.s_id=%s and a.se_id=%s '%(s_id,se_id)
            if week>0: # in one week
                rdata_sql = '%s and a.week=%s order by a.id desc'%(rdata_sql,week)
            else: # in one semester
                rdata_sql = '%s order by a.id desc'%rdata_sql
                
            cursor.execute(rdata_sql)
            a_record = cursor.fetchall()
            if a_record:
                for (id,date,cname,tname,vioval) in a_record:
                    one_rec=[]
                    one_rec.append(id)
                    one_rec.append('{0} {1}({2}) {3}'.format(date,cname,tname,get_vioset_str(vioval)))
                    r_data.append(one_rec)
            output.update({'rdata':r_data})
                
        if(no_sel < 2): # no select(course/students), need to load course/clasess 
            t_type = int(request.values.get('ttype'))
            t_id = request.values.get('tid')
            if(t_type == 2):
                cursor.execute('select id,name from classes where ft_id=%s',t_id)
            else:
                cursor.execute('select c.id,c.sname from courses as c,timetable as tt \
                                where tt.c_id=c.id and tt.t_id=%s group by c.id;',t_id)

            cc_data = cursor.fetchall()
            ccid=[]
            ccdata=[]
            if cc_data:
                for(id,name) in cc_data:
                    ccid.append(id)
                    ccdata.append(name)

            output.update({'ccid':ccid,'ccdata':ccdata})
            
        elif(no_sel == 2): # no (students), need to load students
            c_id = request.values.get('cid')
            t_id = request.values.get('tid')
            t_type = int(request.values.get('ttype'))
            sid = []
            sname=[]

            if(t_type == 2): # form teacher
                cursor.execute('select s.id,s.name,s.eng_name from students as s where s.cl_id=%s',c_id)
            else: # normal teacher
                cursor.execute('select s.id,s.name,s.eng_name from students as s,enrollment as e \
                                where e.s_id = s.id and e.t_id = %s and e.c_id = %s',(t_id,c_id))
            students = cursor.fetchall()
            if students:
                for(id,name,ename) in students:
                    sid.append(id)
                    sname.append('{0}({1})'.format(name,ename))

            output.update({'sid':sid,'sname':sname})
            
    return jsonify(output)
