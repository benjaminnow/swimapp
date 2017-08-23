from __future__ import print_function
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
#import pymysql
#from wtforms import Form, StringField, PasswordField, SelectField, IntegerField, BooleanField, DecimalField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import random
from operator import itemgetter
import json
import httplib2
from apiclient import discovery
from oauth2client import client
import time
import chartkick
from db import *
from forms import *
import os

app = Flask(__name__)
app.jinja_env.add_extension("chartkick.ext.charts")


def isSuperAdmin():
    session_username = session['username']
    conn, cur = connection()
    cur.execute('SELECT * FROM users WHERE username=%s', [session_username])
    name_user = cur.fetchone()
    ids = name_user['id']
    cur.execute('SELECT * FROM users WHERE id=%s', [ids])
    user = cur.fetchone()
    super_admin = user['super_admin']
    conn.close()
    return super_admin

def is_admin():
    session_username = session['username']
    conn, cur = connection()
    cur.execute('SELECT * FROM users WHERE username=%s', [session_username])
    name_user = cur.fetchone()
    ids = name_user['id']
    cur.execute('SELECT * FROM users WHERE id=%s', [ids])
    user = cur.fetchone()
    admin = user['admin']
    conn.close()
    return admin

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Access Denied', 'danger')
            return redirect(url_for('login'))
    return wrap

def is_logged_in_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and is_admin() == 1:
            return f(*args, **kwargs)
        else:
            flash('Access Denied', 'danger')
            return redirect(url_for('login'))
    return wrap

def is_logged_in_super_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and isSuperAdmin() == 1:
            return f(*args, **kwargs)
        else:
            flash('Access Denied', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/swimmers')
@is_logged_in
def swimmers():
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers ORDER BY name ASC")
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('swimmers.html', swimmers = swimmers)
    else:
        msg = 'No swimmers found'
        return render_template('swimmers.html', msg = msg)
    conn.close()

@app.route('/swimmers/<string:id>')
@is_logged_in
def swimmer(id):
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers WHERE id = %s", [id])
    swimmer = cur.fetchone()
    result2 = cur.execute("SELECT * FROM attendance WHERE id = %s", [id])
    attendance_d = cur.fetchall()
    result3 = cur.execute('SELECT * FROM jobs_done_history WHERE id = %s', [id])
    jobs = cur.fetchall()
    swimmerGroup = swimmer['training_group']
    swimmerTotal = swimmer['total']
    result4 = cur.execute('SELECT * FROM set_attendance WHERE training_group=%s', [swimmerGroup])
    if result4 == 0:
        percent = 'NaN'
    else:
        attendance = cur.fetchall()
        attendanceTotal = attendance[0]['total']
        percent = swimmerTotal/attendanceTotal * 100

    cur.execute('SELECT percent, date FROM weekly_attendance_history WHERE id = %s ', [id])
    data = cur.fetchall()
    datalst = []
    for i in range(len(data)):
        date = data[i]['date'].isoformat()
        percent = data[i]['percent']
        datalst.append([date, percent])
    conn.close()
    return render_template('swimmer.html', swimmer = swimmer, attendance_d = attendance_d, jobs = jobs, percent = percent, data=datalst)

@app.route('/swimmers/training_group/<string:group>')
@is_logged_in
def training_group(group):
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers WHERE training_group = %s", [group])
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('swimmers_group.html', swimmers = swimmers)
    else:
        msg = 'No swimmers found'
        return render_template('swimmers_group.html', msg = msg)
    conn.close()

@app.route('/dashboard/training_group/<string:group>', methods = ['GET', 'POST'])
@is_logged_in_admin
def group_dashboard(group):
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers WHERE training_group = %s ORDER BY name ASC", [group])
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('group_dashboard.html', swimmers = swimmers, group=group)
    else:
        msg = 'No swimmers found'
        return render_template('group_dashboard.html', msg = msg)
    conn.close()

def username_already_registered(name):
    conn, cur = connection()
    result = cur.execute('SELECT * FROM users WHERE username = %s', [name])
    conn.close()
    if result > 0:
        return True
    else:
        return False


@app.route('/register', methods = ['GET', 'POST'])
def register():
    isAdmin = False
    isSuperAdmin = False
    conn, cur = connection()
    result = cur.execute("SELECT * FROM admin")
    data = cur.fetchall()
    code1 = data[0]['password']
    code2 = data[1]['password']
    #code = data['password']
    form = RegisterForm(request.form)
    if form.admin_code.data == code1:
        isAdmin = True
    elif form.admin_code.data == code2:
        isSuperAdmin = True
    conn.close()

    if request.method == 'POST' and form.validate() and isAdmin:
        name = form.name.data
        email = form.email.data
        username = form.username.data
        if username_already_registered(username):
            error = 'username is already taken'
            return render_template('register.html', form = form, error = error)
        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute("INSERT INTO users(name, email, username, password, admin) VALUES(%s, %s, %s, %s, 1)", (name, email, username, password))
        conn.commit()
        conn.close()

        flash('You are now registered', 'success')

        return redirect(url_for('login'))

    elif request.method == 'POST' and form.validate() and isSuperAdmin:
        name = form.name.data
        email = form.email.data
        username = form.username.data
        if username_already_registered(username):
            error = 'username is already taken'
            return render_template('register.html', form = form, error = error)
        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute("INSERT INTO users(name, email, username, password, admin, super_admin) VALUES(%s, %s, %s, %s, 1, 1)", (name, email, username, password))
        conn.commit()
        conn.close()

        flash('You are now registered', 'success')

        return redirect(url_for('login'))


    elif request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        if username_already_registered(username):
            error = 'username is already taken'
            return render_template('register.html', form = form, error = error)
        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute("INSERT INTO users(name, email, username, password, admin) VALUES(%s, %s, %s, %s, 0)", (name, email, username, password))
        conn.commit()
        conn.close()

        flash('You are now registered', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form = form)


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        conn, cur = connection()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                error = 'Password does not match'
                return render_template('login.html', error = error)
        else:
            error = 'Username not found'
            return render_template('login.html', error = error)

    return render_template('login.html')


@app.route('/dashboard')
@is_logged_in_admin
def dashboard():
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers ORDER BY name ASC")
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', swimmers = swimmers)
    else:
        msg = 'No swimmers found'
        return render_template('dashboard.html', msg = msg)
    conn.close()



@app.route('/add_swimmer', methods = ['GET', 'POST'])
@is_logged_in_admin
def add_swimmer():
    form = SwimmerForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        group = form.group.data
        conn, cur = connection()
        cur.execute("INSERT INTO swimmers(name, total, training_group) VALUES(%s, 0, %s)", (name, group))
        conn.commit()
        conn.close()
        flash('Swimmer created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_swimmer.html', form = form)

@app.route('/delete_swimmer/<string:id>', methods = ['POST'])
@is_logged_in_admin
def delete_swimmer(id):
    conn, cur = connection()
    count = cur.execute('SELECT * FROM swimmer_limbo')
    if count > 0:
        cur.execute('DELETE FROM swimmer_limbo')
        conn.commit()

    cur.execute("INSERT INTO swimmer_limbo SELECT * FROM swimmers WHERE id=%s", [id])
    conn.commit()
    cur.execute("DELETE FROM swimmers WHERE id=%s", [id])
    conn.commit()
    cur.execute("DELETE FROM attendance WHERE id=%s", [id])
    conn.commit()
    cur.execute("SELECT * FROM swimmers ORDER BY name ASC")
    swimmers = cur.fetchall()
    conn.close()
    flash('Swimmer deleted', 'success')
    undo = 'Undo delete?'
    return render_template('dashboard.html', undo = undo, swimmers = swimmers)

@app.route('/attending/<string:id>', methods = ['POST'])
@is_logged_in_admin
def attending(id):
    conn, cur = connection()
    if request.method == 'POST':
        amount = request.form['amount']
        group_id = request.form['group']
        id_value = request.form['id']
        cur.execute("UPDATE swimmers SET attending = 1, total = total + %s WHERE id=%s", (float(amount), id_value))
        conn.commit()
        cur.execute("INSERT INTO attendance(id, amount) VALUES(%s, %s)",(id_value, float(amount)))
        conn.commit()
        conn.close()
        return redirect(url_for('group_dashboard', group=group_id))


@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    flash(session['credentials'])
    return redirect(url_for('index'))


@app.route('/reset_all_attending', methods = ['POST'])
@is_logged_in_admin
def reset_all_attending():
    conn, cur = connection()
    cur.execute('UPDATE swimmers SET attending = 0')
    conn.commit()
    cur.execute('DELETE FROM here')
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reset_attending/<string:training_g>', methods = ['POST'])
@is_logged_in_admin
def reset_attending(training_g):
    conn, cur = connection()
    cur.execute('UPDATE swimmers SET attending = 0 WHERE training_group=%s', [training_g])
    conn.commit()
    cur.execute('DELETE FROM here WHERE training_group=%s', [training_g])
    conn.commit()
    conn.close()
    return redirect(url_for('group_dashboard', group = training_g))

@app.route('/here')
@is_logged_in_admin
def here():
    conn, cur = connection()
    cur.execute('INSERT IGNORE INTO here(id, name, job_total, training_group) SELECT id, name, job_total, training_group FROM swimmers WHERE attending = 1')
    conn.commit()
    result = cur.execute('SELECT * FROM here')
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('here.html', swimmers = swimmers)
    else:
        msg = 'No swimmers attending found'
        return render_template('here.html', msg = msg)
    conn.close()

@app.route('/remove_here/<string:id>', methods = ['POST'])
@is_logged_in_admin
def remove_here(id):
    conn, cur = connection()
    cur.execute('DELETE FROM here WHERE id=%s', [id])
    conn.commit()
    cur.execute('UPDATE swimmers SET attending = 0 WHERE id=%s', [id])
    conn.commit()
    cur.execute('UPDATE swimmers SET job_total = job_total + 5 WHERE id=%s', [id])
    conn.commit()
    conn.close()
    flash('Swimmer removed from here list', 'success')
    return redirect(url_for('here'))



@app.route('/add_job', methods = ['GET', 'POST'])
@is_logged_in_admin
def add_job():
    form = JobForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        minimum = form.minimum.data
        difficulty = form.difficulty.data
        dump = form.dump.data
        conn, cur = connection()
        if dump:
            result = cur.execute('SELECT * FROM jobs WHERE dump=1')
            if result > 0:
                cur.execute('UPDATE jobs SET dump = 0 WHERE dump = 1')
                conn.commit()
            cur.execute("INSERT INTO jobs(name, minimum, difficulty, dump) VALUES(%s, %s, %s, %s)", (name, int(minimum), int(difficulty), int(1)))
        else:
            cur.execute("INSERT INTO jobs(name, minimum, difficulty) VALUES(%s, %s, %s)", (name, int(minimum), int(difficulty)))
        conn.commit()
        conn.close()
        flash('Job created', 'success')
        return redirect(url_for('jobs'))
    return render_template('add_job.html', form = form)


@app.route('/jobs')
@is_logged_in_admin
def jobs():
    conn, cur = connection()
    cur.execute('SELECT * FROM jobs')
    jobs = cur.fetchall()
    return render_template('jobs.html', jobs = jobs)

@app.route('/remove_job/<string:id>', methods=['POST'])
@is_logged_in_admin
def remove_job(id):
    conn, cur = connection()
    cur.execute('DELETE FROM jobs WHERE id=%s', [id])
    conn.commit()
    return redirect(url_for('jobs'))



def get_min():
    conn, cur = connection()
    cur.execute('SELECT minimum FROM jobs')
    draws = cur.fetchall()
    count = 0
    for i in range(len(draws)):
        count += draws[i]['minimum']
    return count

def get_available():
    conn, cur = connection()
    cur.execute('SELECT COUNT(*) FROM here')
    people = cur.fetchall()
    peoplenum = people[0]['COUNT(*)']
    return peoplenum

def get_job_total():
    conn, cur = connection()
    cur.execute('SELECT job_total FROM here')
    ids = cur.fetchall()
    total = 0
    for i in range(len(ids)):
        total += ids[i]['job_total']
    conn.close()
    return total

def high_low():
    start = 0
    conn, cur = connection()
    cur.execute('SELECT job_total, id FROM here')
    ids = cur.fetchall()
    for i in range(len(ids)):
        low = start
        high = start + ids[i]['job_total']
        start = high
        ids[i]['low'] = low
        ids[i]['high'] = high
    conn.close()
    return ids

def choose_people():
    rangeDict = high_low()
    rangeList = list(high_low())
    total = get_job_total()
    count = get_min()
    idList = []
    start = 0

    for i in range(count):
        randnum = random.randint(1, total + 1)
        for j in range(len(rangeList)):
            if randnum > rangeList[j]['low'] and randnum <= rangeList[j]['high']:
                    idList.append([rangeList[j]['id'], rangeList[j]['job_total']])
                    total -= rangeList[j]['job_total']
                    rangeList.pop(j)
                    break

        for k in range(len(rangeList)):
            low = start
            high = start + rangeList[k]['job_total']
            start = high
            rangeList[k]['low'] = low
            rangeList[k]['high'] = high
        start = 0

    idList.sort(key=itemgetter(1), reverse=True)

    conn, cur = connection()
    cur.execute('SELECT name, difficulty, minimum, id FROM jobs WHERE dump = 1')
    job = cur.fetchall()
    jobName = job[0]['name']
    jobAmount = job[0]['difficulty']
    jobId = job[0]['id']
    for p in range(len(rangeDict)):
        found = False
        for q in range(len(idList)):
            if rangeDict[p]['id'] == idList[q][0]:
                found = True
        idnum = rangeDict[p]['id']
        if not found:
            cur.execute('INSERT IGNORE INTO jobs_done(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (idnum, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('INSERT INTO jobs_done_history(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (idnum, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('UPDATE swimmers set job_total = job_total + %s WHERE id=%s', (int(jobAmount), idnum))
            conn.commit()
    conn.close()

    return idList

@app.route('/choose_jobs')
@is_logged_in_admin
def choose_jobs():
    if get_min() > get_available():
        return render_template('here.html', msg = 'not enough people')


    idList = choose_people()
    conn, cur = connection()
    cur.execute('SELECT * FROM jobs')
    jobs = cur.fetchall()
    jobTuple = []
    for i in range(len(jobs)):
        jobTuple.append([jobs[i]['id'], jobs[i]['minimum'], jobs[i]['difficulty']])
    jobTuple.sort(key=itemgetter(2))

    start = 0
    for k in range(len(jobTuple)):
        jobId = jobTuple[k][0]
        cur.execute('SELECT name, difficulty, minimum FROM jobs WHERE id = %s', [jobId])
        job = cur.fetchall()
        jobName = job[0]['name']
        jobAmount = job[0]['difficulty']
        jobMinimum = job[0]['minimum'] + start

        for j in range(start, jobMinimum):
            selected = idList[j][0]
            cur.execute('INSERT IGNORE INTO jobs_done(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (selected, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('INSERT INTO jobs_done_history(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (selected, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('UPDATE swimmers set job_total = job_total + %s WHERE id=%s', (int(jobAmount), selected))
            conn.commit()
        start = jobMinimum
    conn.close()
    return redirect(url_for('chosen_jobs'))

@app.route('/chosen_jobs')
@is_logged_in_admin
def chosen_jobs():
    conn, cur = connection()
    cur.execute('SELECT * FROM jobs_done')
    chosenSwimmers = cur.fetchall()

    cur.execute('SELECT * FROM jobs')
    jobs = cur.fetchall()

    cur.execute('SELECT * FROM swimmers')
    swimmers = cur.fetchall()
    conn.close()
    return render_template('chosen_jobs.html', jobs = jobs, chosenSwimmers = chosenSwimmers, swimmers = swimmers)

@app.route('/delete_chosen')
@is_logged_in_admin
def delete_chosen():
    conn, cur = connection()
    cur.execute('DELETE FROM jobs_done')
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/take_credit/<string:id>', methods = ['POST'])
@is_logged_in_admin
def take_credit(id):
    conn, cur = connection()
    if request.method == 'POST':
        amount = request.form['amount']
        id_value = request.form['id']
        cur.execute("UPDATE swimmers SET job_total = job_total - %s WHERE id=%s", (float(amount), id_value))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))


def update_percent():
    conn, cur = connection()
    cur.execute('SELECT name, training_group, total, id FROM swimmers')
    swimmers = cur.fetchall()

    for i in range(len(swimmers)):
        swimmerID = swimmers[i]['id']
        swimmerTotal = swimmers[i]['total']
        swimmerGroup = swimmers[i]['training_group']
        swimmerName = swimmers[i]['name']
        cur.execute('SELECT total FROM set_attendance WHERE training_group = %s', [swimmerGroup])
        attendance = cur.fetchall()
        attendanceTotal = attendance[0]['total']
        if attendanceTotal == 0:
            percent = None
        else:
            percent = swimmerTotal / attendanceTotal * 100
            cur.execute('UPDATE swimmers SET percent = %s WHERE id=%s', (float(percent), swimmerID))
            conn.commit()

    conn.close()

@app.route('/attendance')
@is_logged_in_admin
def attendance():
    conn, cur = connection()
    cur.execute('SELECT * FROM set_attendance')
    attendance_totals = cur.fetchall()
    cur.execute('SELECT * FROM set_attendance_history')
    attendance_history = cur.fetchall()
    return render_template('attendance.html', attendance_totals = attendance_totals, attendance_history = attendance_history)



@app.route('/add_attendance', methods = ['GET', 'POST'])
@is_logged_in_admin
def add_attendance():
    form = AttendanceForm(request.form)
    if request.method == 'POST' and form.validate:
        conn, cur = connection()
        amount = form.amount.data
        group = form.group.data
        result = cur.execute('SELECT * FROM set_attendance WHERE training_group=%s', [group])
        if result == 0:
            cur.execute('INSERT INTO set_attendance(training_group, total) VALUES(%s, %s)', (group, float(amount)))
            conn.commit()
            cur.execute('INSERT INTO set_attendance_history(training_group, amount) VALUES(%s, %s)', (group, float(amount)))
            conn.commit()
            update_percent()
            conn.close()
            return redirect(url_for('attendance'))
        else:
            cur.execute('UPDATE set_attendance SET total = total + %s WHERE training_group = %s', (float(amount), group))
            conn.commit()
            cur.execute('INSERT INTO set_attendance_history(training_group, amount) VALUES(%s, %s)', (group, float(amount)))
            conn.commit()
            update_percent()
            conn.close()
            return redirect(url_for('attendance'))
    return render_template('add_attendance.html', form = form)

@app.route('/undo_delete')
@is_logged_in_admin
def undo_delete():
    conn, cur = connection()
    cur.execute('INSERT INTO swimmers SELECT * FROM swimmer_limbo')
    conn.commit()
    cur.execute('DELETE FROM swimmer_limbo')
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/archive')
@is_logged_in_super_admin
def archive_page():
    return render_template('archive.html')

@app.route('/oauth2callback')
def oauth2callback():
  flow = client.flow_from_clientsecrets(
      'client_secret_local.json',
      scope='https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive',
      redirect_uri=url_for('oauth2callback', _external=True)
      )
  flow.params['include_granted_scopes'] = 'true'
  #flow.params['access_type'] = 'offline'
  if 'code' not in request.args:
    auth_uri = flow.step1_get_authorize_url()
    return redirect(auth_uri)
  else:
    auth_code = request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    session['credentials'] = credentials.to_json()
    return redirect(url_for('archive_page'))

@app.route('/login_to_google')
@is_logged_in_super_admin
def login_to_google():
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))
    return redirect(url_for('archive_page'))


@app.route('/archive/<string:id>')
@is_logged_in_super_admin
def archive(id):
    conn, cur = connection()
    if id == 'job_total':
        cur.execute('UPDATE swimmers SET job_total = 0')
        conn.commit()
        conn.close()
        return redirect(url_for('archive_page'))
    elif id == 'attendance_total':
        cur.execute('UPDATE swimmers SET total = 0, attending = 0')
        conn.commit()
        conn.close()
        return redirect(url_for('archive_page'))
    elif id == 'group_attendance':
        cur.execute('UPDATE set_attendance SET total = 0')
        conn.commit()
        cur.execute('DELETE FROM set_attendance_history')
        conn.commit()
        conn.close()
        return redirect(url_for('archive_page'))
    elif id == 'weekly_attendance_history':
        cur.execute('DELETE FROM weekly_attendance_history')
        conn.commit()
        conn.close()
        return redirect(url_for('archive_page'))
    else:
        return redirect(url_for('dashboard'))


@app.route('/weekly_attendance/<string:training_group>')
@is_logged_in_super_admin
def weekly_attendance(training_group):
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    conn, cur = connection()
    # creates the google sheet
    http_auth = credentials.authorize(httplib2.Http())
    SHEETS = discovery.build('sheets', 'v4', http_auth)
    data = {'properties': {'title': 'Attendance [%s] [%s]' % (training_group, time.ctime())}}
    res = SHEETS.spreadsheets().create(body=data).execute()
    SHEET_ID = res['spreadsheetId']
    file_id = str(SHEET_ID)
    print(SHEET_ID)
    print('Created "%s"' % res['properties']['title'])
    # gets data from the weekly attendance function
    data = get_weekly_attendance(training_group)
    # puts data into spreadsheet
    SHEETS.spreadsheets().values().update(spreadsheetId=SHEET_ID,
        range='A1', body=data, valueInputOption='RAW').execute()
    #print('Wrote data to Sheet:')
    rows = SHEETS.spreadsheets().values().get(spreadsheetId=SHEET_ID,
        range='Sheet1').execute().get('values', [])
    cur.execute('DELETE FROM weekly_attendance')
    conn.commit()
    conn.close()
    return redirect(url_for('archive_page'))



def get_weekly_attendance(training_group):
    conn, cur = connection()
    # make selection between all the training groups or just one
    if training_group == 'all':
        cur.execute('SELECT * FROM swimmers')
    else:
        cur.execute('SELECT * FROM swimmers WHERE training_group = %s', [training_group])
    swimmers = cur.fetchall()
    # loops through swimmers in a training group
    # grabs their group, total, name, id
    for i in range(len(swimmers)):
        swimmerGroup = swimmers[i]['training_group']
        swimmerTotal = swimmers[i]['total']
        swimmerName = swimmers[i]['name']
        swimmerID = swimmers[i]['id']
        result = cur.execute('SELECT * FROM set_attendance WHERE training_group=%s', [swimmerGroup])
        # checks to see if any swimmers in group
        if result == 0:
            #checks if percent == null
            percent = None
            cur.execute('INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, 0)', (int(swimmerID), swimmerName, percent, float(swimmerTotal)))
            conn.commit()
        else:
            # gets attendance from db
            attendance = cur.fetchall()
            attendanceTotal = attendance[0]['total']
            # make sure attendance total does not = 0 so no divide by 0 error
            if attendanceTotal == 0:
                percent = None
                cur.execute('INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, 0)', (int(swimmerID), swimmerName, percent, float(swimmerTotal)))
                conn.commit()
            else:
                # calculates percent if attendance total doesn't equal 0
                percent = swimmerTotal/attendanceTotal * 100
                cur.execute('INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s)', (int(swimmerID), swimmerName, float(percent), float(swimmerTotal), float(attendanceTotal)))
                conn.commit()

    # headers at top of spreadsheet
    FIELDS = ('Name', 'Percent', 'Total', 'A_Total')
    # grab all data from weekly_attendance
    cur.execute('SELECT name, percent, total, attendance_total FROM weekly_attendance')
    rows = cur.fetchall()
    rows = list(rows)
    newRows = []
    # format DictCursor from db into a list of lists that google sheets can read
    for row in rows:
        tmp = []
        for key, value in row.iteritems():
            if key == 'percent':
                tmp.append(str(value) + '%')
            else:
                tmp.append(value)
        tmp = tmp[::-1]
        newRows.append(tmp)
        tmp = []
    newRows.insert(0, FIELDS)
    data = {'values': [row[0:] for row in newRows]}
    cur.execute('INSERT INTO weekly_attendance_history(id, name, percent, total, attendance_total) SELECT id, name, percent, total, attendance_total FROM weekly_attendance')
    conn.commit()
    cur.execute('DELETE FROM weekly_attendance')
    conn.commit()
    conn.close()
    return data

@app.route('/end_season_attendance')
@is_logged_in_super_admin
def end_season_attendance():
    # connects to google if not connected already
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    conn, cur = connection()
    http_auth = credentials.authorize(httplib2.Http())
    SHEETS = discovery.build('sheets', 'v4', http_auth)
    data = {'properties': {'title': 'End of season attendance [%s]' % time.ctime()}}
    res = SHEETS.spreadsheets().create(body=data).execute()
    SHEET_ID = res['spreadsheetId']
    file_id = str(SHEET_ID)
    print(SHEET_ID)
    print('Created "%s"' % res['properties']['title'])
    data = get_end_attendance()
    SHEETS.spreadsheets().values().update(spreadsheetId=SHEET_ID,
        range='A1', body=data, valueInputOption='RAW').execute()
    #print('Wrote data to Sheet:')
    rows = SHEETS.spreadsheets().values().get(spreadsheetId=SHEET_ID,
        range='Sheet1').execute().get('values', [])
    cur.execute('DELETE FROM season_attendance')
    conn.commit()
    conn.close()
    return redirect(url_for('archive_page'))

def get_end_attendance():
    conn, cur = connection()
    cur.execute('SELECT * FROM swimmers')
    swimmers = cur.fetchall()
    cur.execute('SELECT training_group FROM set_attendance')
    groups = cur.fetchall()
    for i in range(len(swimmers)):
        swimmerGroup = swimmers[i]['training_group']
        swimmerTotal = swimmers[i]['total']
        swimmerName = swimmers[i]['name']
        swimmerID = swimmers[i]['id']
        result = cur.execute('SELECT * FROM set_attendance WHERE training_group=%s', [swimmerGroup])
        if result == 0:
            percent = None
            cur.execute('INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, 0)', (int(swimmerID), swimmerName, swimmerGroup, percent, float(swimmerTotal)))
            conn.commit()
        else:
            attendance = cur.fetchall()
            attendanceTotal = attendance[0]['total']
            if attendanceTotal == 0:
                percent = None
                cur.execute('INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, 0)', (int(swimmerID), swimmerName, swimmerGroup, percent, float(swimmerTotal)))
                conn.commit()
            else:
                percent = swimmerTotal/attendanceTotal * 100
                cur.execute('INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, %s)', (int(swimmerID), swimmerName, swimmerGroup, float(percent), float(swimmerTotal), float(attendanceTotal)))
                conn.commit()

    groupList = []
    for i in range(len(groups)):
        groupList.append(groups[i]['training_group'])

    totalRows = []
    # top of the spreadsheet
    FIELDS = ('Name', 'Percent', 'Total', 'A_Total')
    for group in groupList:
        cur.execute('SELECT name, percent, total, attendance_total FROM season_attendance WHERE training_group = %s', [group])
        rows = cur.fetchall()
        rows = list(rows)
        newRows = []
        for row in rows:
            tmp = []
            for key, value in row.iteritems():
                if key == 'percent':
                    tmp.append(str(value) + '%')
                else:
                    tmp.append(value)
            tmp = tmp[::-1]
            newRows.append(tmp)
            tmp = []

        header = [group]
        for i in range(len(FIELDS) - 1):
            header.append('')
        header = tuple(header)

        spacer = []
        for i in range(len(FIELDS)):
            spacer.append('')
        spacer = tuple(spacer)

        newRows.insert(0, header)
        #newRows.insert(1, spacer)
        newRows.insert(1, FIELDS)
        for i in range(2, 6):
            newRows.append(spacer)

        totalRows.append(newRows)
        newRows = []

    finalRows = []
    for i in range(len(totalRows)):
        for row in totalRows[i]:
            finalRows.append(row)

    #data = {'values': [row[0:] for row in finalRows]}
    data = {'values': [row for row in finalRows]}
    cur.execute('DELETE FROM season_attendance')
    conn.commit()
    conn.close()
    return data

# @app.route('/charts/top/all')
# @is_logged_in
# def charts():
#     conn, cur = connection()
#     cur.execute('SELECT name, percent FROM swimmers ORDER BY percent DESC')
#     swimmers = cur.fetchall()
#
#     dataList = []
#     for i in range(len(swimmers)):
#         swimmerPercent = swimmers[i]['percent']
#         swimmerName = swimmers[i]['name']
#
#         dataList.append([str(swimmerName), swimmerPercent])
#
#     conn.close()
#     return render_template('charts.html', data = dataList)
#
# @app.route('/charts/top/<string:training_group>')
# @is_logged_in
# def chartsgroup(training_group):
#     conn, cur = connection()
#     cur.execute('SELECT name, percent FROM swimmers WHERE training_group = %s ORDER BY percent DESC', [training_group])
#     swimmers = cur.fetchall()
#
#     dataList = []
#     for i in range(len(swimmers)):
#         swimmerPercent = swimmers[i]['percent']
#         swimmerName = swimmers[i]['name']
#
#         dataList.append([str(swimmerName), swimmerPercent])
#
#     conn.close()
#     return render_template('chartsgroup.html', data = dataList)

# comment out this when on local machine
if __name__ == '__main__':
    app.secret_key = str(os.urandom(24))
    app.run(debug = True)

# comment in this when pushing to webserver
#app.secret_key = str(os.urandom(24))
