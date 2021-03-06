from __future__ import print_function
from flask import Flask, render_template, flash, redirect, url_for, session, request, jsonify
from passlib.hash import sha256_crypt
from functools import wraps
import string
import chartkick
from forms import *
from job_choosing import *
import os
from apiclient import discovery
from oauth2client import client
import time
import httplib2


app = Flask(__name__)
app.secret_key = "SUPERSECRETKEY"
app.jinja_env.add_extension("chartkick.ext.charts")


def isSuperAdmin():
    session_username = session['username']
    conn, cur = connection()
    cur.execute('SELECT * FROM users WHERE username=%s', [session_username])
    name_user = cur.fetchall()
    super_admin = name_user[0]['super_admin']
    conn.close()
    return super_admin


def is_admin():
    session_username = session['username']
    conn, cur = connection()
    cur.execute('SELECT * FROM users WHERE username=%s', [session_username])
    name_user = cur.fetchall()
    admin = name_user[0]['admin']
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


@is_logged_in
def get_session_id():
    session_username = session['username']
    conn, cur = connection()
    cur.execute('SELECT id FROM users WHERE username=%s', [session_username])
    name_user = cur.fetchall()
    idnum = name_user[0]['id']
    conn.close()
    return idnum


@app.route('/')
def index():
    if 'logged_in' in session:
        admin_check = isSuperAdmin()
    else:
        admin_check = 0
    conn, cur = connection()
    result = cur.execute('SELECT * FROM quote')
    if result > 0:
        quote = cur.fetchall()
        body = quote[0]['quote_text']
        author = quote[0]['author']
        return render_template('home.html', admin_check=admin_check, body=body, author=author)
    else:
        return render_template('home.html', admin_check=admin_check)


def get_group_list():
    conn, cur = connection()
    cur.execute('SELECT training_group FROM set_attendance')
    groups = cur.fetchall()
    group_list = []
    for i in range(len(groups)):
        group_list.append(groups[i]['training_group'])
    return group_list


@app.route('/swimmers')
@is_logged_in
def swimmers():
    group_list = get_group_list()
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers ORDER BY name ASC")
    swimmers = cur.fetchall()
    if result > 0:
        conn.close()
        return render_template('swimmers.html', swimmers=swimmers, group_list=group_list)
    else:
        msg = 'No swimmers found'
        conn.close()
        return render_template('swimmers.html', msg=msg, group_list=group_list)



@app.route('/swimmers/<string:id>')
@is_logged_in
def swimmer(id):
    conn, cur = connection()
    form = EditAttendanceForm(request.form)
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
        if attendanceTotal == 0:
            percent = 'NaN'
        else:
            percent = swimmerTotal / attendanceTotal * 100

    cur.execute('SELECT percent, date FROM weekly_attendance_history WHERE id = %s ', [id])
    data = cur.fetchall()
    datalst = []
    for i in range(len(data)):
        date = data[i]['date'].isoformat()
        percent = data[i]['percent']
        datalst.append([date, percent])
    conn.close()
    return render_template('swimmer.html', swimmer=swimmer, attendance_d=attendance_d, jobs=jobs, percent=percent,
                           data=datalst, form=form)


@app.route('/swimmers/training_group/<string:group>')
@is_logged_in
def training_group(group):
    group_list = get_group_list()
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers WHERE training_group = %s", [group])
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('swimmers_group.html', swimmers=swimmers, group_list=group_list)
    else:
        msg = 'No swimmers found'
        return render_template('swimmers_group.html', msg=msg, group_list=group_list)
    conn.close()


@app.route('/dashboard/training_group/<string:group>', methods=['GET', 'POST'])
@is_logged_in_admin
def group_dashboard(group):
    group_list = get_group_list()
    form = RemoveAttendanceForm(request.form)
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers WHERE training_group = %s", [group])
    swimmers = cur.fetchall()
    cur.execute("SELECT * FROM attendance_amounts ORDER BY amount ASC")
    amounts = cur.fetchall()
    cur.execute('SELECT * FROM default_values')
    default_values = cur.fetchall()
    if result > 0:
        return render_template('group_dashboard.html', swimmers=swimmers, group=group, form=form, group_list=group_list,
                               amounts=amounts, default_values=default_values)
    else:
        msg = 'No swimmers found'
        return render_template('group_dashboard.html', msg=msg, group=group, form=form, group_list=group_list)
    conn.close()


def username_already_registered(name):
    conn, cur = connection()
    result = cur.execute('SELECT * FROM users WHERE username = %s', [name])
    conn.close()
    if result > 0:
        return True
    else:
        return False


def access_code_used(code):
    conn, cur = connection()
    result = cur.execute('SELECT id FROM swimmers WHERE code = %s', [code])
    if result > 0:
        ids = cur.fetchall()
        swimmer_id = ids[0]['id']
        result2 = cur.execute('SELECT * FROM users WHERE linked_swimmer = %s', [swimmer_id])
        conn.close()
        if result2 > 0:
            return 1
        else:
            return 0
    else:
        return 2


@app.route('/register', methods=['GET', 'POST'])
def register():
    isAdmin = False
    isSuperAdmin = False
    conn, cur = connection()
    result = cur.execute("SELECT * FROM admin")
    data = cur.fetchall()
    code1 = data[0]['password']
    code2 = data[1]['password']
    # code = data['password']
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
            return render_template('register.html', form=form, error=error)
        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute("INSERT INTO users(name, email, username, password, admin) VALUES(%s, %s, %s, %s, 1)",
                    (name, email, username, password))
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
            return render_template('register.html', form=form, error=error)
        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute(
            "INSERT INTO users(name, email, username, password, admin, super_admin) VALUES(%s, %s, %s, %s, 1, 1)",
            (name, email, username, password))
        conn.commit()
        conn.close()

        flash('You are now registered', 'success')

        return redirect(url_for('login'))


    elif request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        access_code = form.access_code.data
        if username_already_registered(username):
            error = 'username is already taken'
            return render_template('register.html', form=form, error=error)
        elif access_code_used(access_code) == 1:
            error = 'access code already used'
            return render_template('register.html', form=form, error=error)
        elif access_code_used(access_code) == 2:
            error = 'access code not valid'
            return render_template('register.html', form=form, error=error)

        password = sha256_crypt.encrypt(str(form.password.data))

        conn, cur = connection()
        cur.execute('SELECT id FROM swimmers WHERE code = %s', [access_code])
        ids = cur.fetchall()
        swimmer_id = ids[0]['id']
        cur.execute(
            "INSERT INTO users(name, email, username, password, linked_swimmer, admin) VALUES(%s, %s, %s, %s, %s, 0)",
            (name, email, username, password, swimmer_id))
        conn.commit()
        conn.close()

        flash('You are now registered', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
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
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/dashboard')
@is_logged_in_admin
def dashboard():
    group_list = get_group_list()
    form = RemoveAttendanceForm(request.form)
    conn, cur = connection()
    result = cur.execute("SELECT * FROM swimmers")
    swimmers = cur.fetchall()
    cur.execute("SELECT * FROM attendance_amounts ORDER BY amount ASC")
    amounts = cur.fetchall()
    cur.execute('SELECT * FROM default_values')
    default_values = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', swimmers=swimmers, form=form, group_list=group_list, amounts=amounts,
                               default_values=default_values)
    else:
        msg = 'No swimmers found'
        return render_template('dashboard.html', msg=msg, form=form, group_list=group_list)
    conn.close()


def id_generator(size=9, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(size))


@app.route('/add_swimmer', methods=['GET', 'POST'])
@is_logged_in_admin
def add_swimmer():
    form = SwimmerForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        group = form.group.data
        code_string = id_generator()
        conn, cur = connection()
        cur.execute("INSERT INTO swimmers(name, total, training_group, code) VALUES(%s, 0, %s, %s)",
                    (name, group, code_string))
        conn.commit()
        conn.close()
        flash('Swimmer created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_swimmer.html', form=form)


@app.route('/delete_swimmer/<string:id>', methods=['POST'])
@is_logged_in_admin
def delete_swimmer(id):
    group_list = get_group_list()
    form = RemoveAttendanceForm(request.form)
    conn, cur = connection()
    cur.execute("SELECT * FROM attendance_amounts")
    amounts = cur.fetchall()
    count = cur.execute('SELECT * FROM swimmer_limbo')
    cur.execute('SELECT * FROM default_values')
    default_values = cur.fetchall()
    if count > 0:
        cur.execute('DELETE FROM swimmer_limbo')
        conn.commit()

    cur.execute("INSERT INTO swimmer_limbo SELECT * FROM swimmers WHERE id=%s", [id])
    conn.commit()
    cur.execute("DELETE FROM swimmers WHERE id=%s", [id])
    conn.commit()
    cur.execute("DELETE FROM attendance WHERE id=%s", [id])
    conn.commit()
    cur.execute("SELECT * FROM swimmers")
    swimmers = cur.fetchall()
    conn.close()
    flash('Swimmer deleted', 'success')
    undo = 'Undo delete?'
    return render_template('dashboard.html', undo=undo, swimmers=swimmers, form=form, group_list=group_list,
                           amounts=amounts, default_values=default_values)


@app.route('/attending', methods=['POST'])
@is_logged_in_admin
def attending():
    if request.method == 'POST':
        conn, cur = connection()
        amount = request.form['amount']
        group_id = request.form['group']
        id_value = request.form['id']
        cur.execute('SELECT total FROM swimmers WHERE id=%s', [id_value])
        current_amount = cur.fetchall()[0]['total']
        cur.execute("UPDATE swimmers SET attending = 1, total = total + %s WHERE id=%s", (float(amount), id_value))
        conn.commit()
        cur.execute("INSERT INTO attendance(id, amount) VALUES(%s, %s)", (id_value, float(amount)))
        conn.commit()
        cur.execute(
            'INSERT IGNORE INTO here(id, name, job_total, training_group) SELECT id, name, job_total, training_group FROM swimmers WHERE attending = 1')
        conn.commit()
        conn.close()
        new_amount = current_amount + float(amount)
        return jsonify({'id': id_value, 'amount': new_amount})


@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))


@app.route('/reset_all_attending', methods=['POST'])
@is_logged_in_admin
def reset_all_attending():
    conn, cur = connection()
    cur.execute('UPDATE swimmers SET attending = 0')
    conn.commit()
    cur.execute('DELETE FROM here')
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/reset_attending/<string:training_g>', methods=['POST'])
@is_logged_in_admin
def reset_attending(training_g):
    conn, cur = connection()
    cur.execute('UPDATE swimmers SET attending = 0 WHERE training_group=%s', [training_g])
    conn.commit()
    cur.execute('DELETE FROM here WHERE training_group=%s', [training_g])
    conn.commit()
    conn.close()
    return redirect(url_for('group_dashboard', group=training_g))


@app.route('/here')
@is_logged_in_admin
def here():
    conn, cur = connection()
    result = cur.execute('SELECT * FROM here')
    swimmers = cur.fetchall()
    if result > 0:
        return render_template('here.html', swimmers=swimmers, count=result)
    else:
        msg = 'No swimmers attending found'
        return render_template('here.html', msg=msg, count=result)
    conn.close()


@app.route('/remove_here/<string:id>', methods=['POST'])
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


@app.route('/add_job', methods=['GET', 'POST'])
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
            cur.execute("INSERT INTO jobs(name, minimum, difficulty, dump) VALUES(%s, %s, %s, %s)",
                        (name, int(minimum), int(difficulty), int(1)))
        else:
            cur.execute("INSERT INTO jobs(name, minimum, difficulty) VALUES(%s, %s, %s)",
                        (name, int(minimum), int(difficulty)))
        conn.commit()
        conn.close()
        flash('Job created', 'success')
        return redirect(url_for('jobs'))
    return render_template('add_job.html', form=form)


@app.route('/jobs')
@is_logged_in_admin
def jobs():
    conn, cur = connection()
    cur.execute('SELECT * FROM jobs')
    jobs = cur.fetchall()
    return render_template('jobs.html', jobs=jobs)


@app.route('/remove_job/<string:id>', methods=['POST'])
@is_logged_in_admin
def remove_job(id):
    conn, cur = connection()
    cur.execute('DELETE FROM jobs WHERE id=%s', [id])
    conn.commit()
    conn.close()
    return redirect(url_for('jobs'))


@app.route('/choose_jobs')
@is_logged_in_admin
def choose_jobs():
    if get_min() > get_available():
        return render_template('here.html', msg='not enough people')

    idList = choose_people()
    conn, cur = connection()
    cur.execute('SELECT * FROM jobs')
    jobs = cur.fetchall()
    jobList = []
    for i in range(len(jobs)):
        jobList.append([jobs[i]['id'], jobs[i]['name'], jobs[i]['minimum'], jobs[i]['difficulty']])
    jobList.sort(key=itemgetter(2))

    start = 0
    for k in range(len(jobList)):
        jobId = jobList[k][0]
        jobName = jobList[k][1]
        jobAmount = jobList[k][3]
        jobMinimum = jobList[k][2] + start

        for j in range(start, jobMinimum):
            selected = idList[j][0]
            cur.execute('INSERT IGNORE INTO jobs_done(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)',
                        (selected, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('INSERT INTO jobs_done_history(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)',
                        (selected, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('UPDATE swimmers SET job_total = job_total + %s WHERE id=%s', (int(jobAmount), selected))
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
    return render_template('chosen_jobs.html', jobs=jobs, chosenSwimmers=chosenSwimmers, swimmers=swimmers)


@app.route('/delete_chosen')
@is_logged_in_admin
def delete_chosen():
    conn, cur = connection()
    cur.execute('DELETE FROM jobs_done')
    conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/take_credit/<string:id>', methods=['POST'])
@is_logged_in_admin
def take_credit(id):
    if request.method == 'POST':
        conn, cur = connection()
        amount = request.form['amount']
        amount = int(amount)
        id_value = request.form['id']
        cur.execute('SELECT job_total FROM swimmers WHERE id = %s', [id_value])
        total = cur.fetchall()
        total = total[0]['job_total']
        if total - amount < 1:
            cur.execute('UPDATE swimmers SET job_total = 1 WHERE id = %s', [id_value])
            conn.commit()
        else:
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
    return render_template('attendance.html', attendance_totals=attendance_totals,
                           attendance_history=attendance_history)


@app.route('/add_group', methods=['GET', 'POST'])
@is_logged_in_super_admin
def add_group():
    form = GroupForm(request.form)
    if request.method == 'POST' and form.validate:
        conn, cur = connection()
        name = form.name.data
        cur.execute('INSERT INTO set_attendance(training_group, total) VALUES(%s, 0)', [name])
        conn.commit()
        conn.close()
        return redirect(url_for('attendance'))
    return render_template('add_group.html', form=form)


@app.route('/add_attendance', methods=['GET', 'POST'])
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
            cur.execute('INSERT INTO set_attendance_history(training_group, amount) VALUES(%s, %s)',
                        (group, float(amount)))
            conn.commit()
            update_percent()
            conn.close()
            return redirect(url_for('attendance'))
        else:
            cur.execute('UPDATE set_attendance SET total = total + %s WHERE training_group = %s',
                        (float(amount), group))
            conn.commit()
            cur.execute('INSERT INTO set_attendance_history(training_group, amount) VALUES(%s, %s)',
                        (group, float(amount)))
            conn.commit()
            update_percent()
            conn.close()
            return redirect(url_for('attendance'))
    return render_template('add_attendance.html', form=form)


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


@app.route('/quote_of_the_day', methods=['GET', 'POST'])
@is_logged_in_super_admin
def quote_of_the_day():
    form = QuoteForm(request.form)
    if request.method == 'POST' and form.validate():
        quote = form.body.data
        author = form.author.data
        conn, cur = connection()
        result = cur.execute('SELECT * FROM quote')
        if result > 0:
            cur.execute('DELETE FROM quote')
            conn.commit()
        cur.execute('INSERT INTO quote(quote_text, author) VALUES(%s, %s)', (quote, author))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_quote.html', form=form)


@app.route('/remove_attendance/<string:id>', methods=['GET', 'POST'])
@is_logged_in_admin
def remove_attendance(id):
    form = RemoveAttendanceForm(request.form)
    if request.method == 'POST' and form.validate():
        conn, cur = connection()
        amount = float(form.amount.data)
        if amount > 9.99:
            return redirect(url_for('dashboard'))
        cur.execute('SELECT total FROM swimmers WHERE id = %s', [id])
        total = cur.fetchall()
        total = total[0]['total']
        if total - amount < 1:
            cur.execute('UPDATE swimmers SET total = 0, attending = 0 WHERE id = %s', [id])
            conn.commit()
            cur.execute('INSERT INTO attendance(id, amount) VALUES(%s, %s)', (id, amount * (-1)))
            conn.commit()
        else:
            cur.execute("UPDATE swimmers SET total = total - %s, attending = 0 WHERE id=%s", (amount, id))
            conn.commit()
            cur.execute('INSERT INTO attendance(id, amount) VALUES(%s, %s)', (id, amount * (-1)))
            conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))


@app.route('/custom_amounts')
@is_logged_in_admin
def custom_amounts():
    conn, cur = connection()
    result = cur.execute('SELECT * FROM attendance_amounts')
    amounts = cur.fetchall()
    return render_template('custom_amounts.html', amounts=amounts)


@app.route('/add_custom_amounts', methods=['GET', 'POST'])
@is_logged_in_admin
def add_custom_amounts():
    form = CustomAmount(request.form)
    if request.method == 'POST' and form.validate():
        amount = float(form.amount.data)
        conn, cur = connection()
        result = cur.execute('SELECT * FROM attendance_amounts')
        if result > 0:
            amounts = cur.fetchall()
            for i in range(len(amounts)):
                if amounts[i]['amount'] == amount:
                    error = 'amount already added'
                    return render_template('add_custom_amount.html', error=error)
        cur.execute('INSERT INTO attendance_amounts(amount) VALUES(%s)', [amount])
        conn.commit()
        conn.close()
        return redirect(url_for('custom_amounts'))
    return render_template('add_custom_amount.html', form=form)


@app.route('/remove_amount/<string:id>', methods=['POST'])
@is_logged_in_admin
def remove_amount(id):
    conn, cur = connection()
    cur.execute('DELETE FROM attendance_amounts WHERE id=%s', [id])
    conn.commit()
    conn.close()
    return redirect(url_for('custom_amounts'))


@app.route('/add_default_values', methods=['GET', 'POST'])
@is_logged_in_admin
def add_default_values():
    form = DefaultValue(request.form)
    if request.method == 'POST' and form.validate():
        conn, cur = connection()
        amount = float(form.amount.data)
        group = form.group.data
        result = cur.execute('SELECT * FROM default_values WHERE training_group=%s', [group])
        if result > 0:
            cur.execute('DELETE FROM default_values WHERE training_group=%s', [group])
            conn.commit()
            cur.execute('INSERT INTO default_values(training_group, value) VALUES(%s, %s)', (group, amount))
            conn.commit()
            return redirect(url_for('default_values'))
        else:
            cur.execute('INSERT INTO default_values(training_group, value) VALUES(%s, %s)', (group, amount))
            conn.commit()
            return redirect(url_for('default_values'))
        conn.close()
    return render_template('add_default_values.html', form=form)


@app.route('/default_values')
@is_logged_in_admin
def default_values():
    conn, cur = connection()
    cur.execute('SELECT * FROM default_values')
    values = cur.fetchall()
    conn.close()
    return render_template('default_values.html', values=values)


@app.route('/remove_default_value/<string:id>', methods=['POST'])
@is_logged_in_admin
def remove_default_value(id):
    conn, cur = connection()
    cur.execute('DELETE FROM default_values WHERE id=%s', [id])
    conn.commit()
    conn.close()
    return redirect(url_for('default_values'))


@app.route('/configure')
@is_logged_in_admin
def configure():
    conn, cur = connection()
    idnum = get_session_id()
    cur.execute('SELECT default_group FROM users WHERE id=%s', [idnum])
    group = cur.fetchall()[0]['default_group']
    return render_template('configure.html', group=group)


@app.route('/set_default_group', methods=['GET', 'POST'])
@is_logged_in_admin
def set_default_group():
    form = DefaultGroup(request.form)
    if request.method == 'POST' and form.validate():
        conn, cur = connection()
        idnum = get_session_id()
        group = form.group.data
        cur.execute('UPDATE users SET default_group=%s WHERE id=%s', (group, idnum))
        conn.commit()
        conn.close()
        return redirect(url_for('configure'))
    return render_template('set_default_group.html', form=form)


@app.context_processor
def change_dashboard():
    if 'logged_in' in session:
        conn, cur = connection()
        cur.execute('SELECT default_group FROM users WHERE id=%s', [get_session_id()])
        navbar_group = cur.fetchall()[0]['default_group']
        return dict(navbar_group=navbar_group)
    else:
        return dict(navbar_group='none')


@is_logged_in_admin
@app.route('/edit/<string:idn>', methods=['GET', 'POST'])
def edit(idn):
    form = EditSwimmer(request.form)
    if request.method == 'POST':
        conn, cur = connection()
        group = form.group.data
        cur.execute('SELECT * FROM swimmers WHERE id=%s', [idn])
        redirect_group = cur.fetchall()[0]['training_group']
        cur.execute('UPDATE swimmers SET training_group=%s WHERE id=%s', (group, idn))
        conn.commit()
        conn.close()
        return redirect(url_for('group_dashboard', group=redirect_group))
    return render_template('edit_swimmer.html', form=form)


@is_logged_in
@app.route('/tutorial')
def tutorial():
    return render_template('gifs.html')


@is_logged_in_admin
@app.route('/change_attendance/<string:idn>/<string:datestr>', methods=['GET', 'POST'])
def change_attendance(idn, datestr):
    form = EditAttendanceForm(request.form)
    if request.method == 'POST':
        conn, cur = connection()
        amount = form.amount.data
        cur.execute('UPDATE attendance SET amount=%s WHERE id=%s AND date=%s', (amount, idn, datestr))
        conn.commit()
        conn.close()
        return redirect(url_for('swimmer', id=idn))
    return redirect(url_for('swimmer', id=idn))



@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secret_local.json',
        scope='https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive',
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.params['include_granted_scopes'] = 'true'
    # flow.params['access_type'] = 'offline'
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
        cur.execute('UPDATE swimmers SET job_total = 1, attending = 0')
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


def export_to_sheets(name, data):
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    http_auth = credentials.authorize(httplib2.Http())
    SHEETS = discovery.build('sheets', 'v4', http_auth)
    head = {'properties': {'title': str(name)}}
    res = SHEETS.spreadsheets().create(body=head).execute()
    SHEET_ID = res['spreadsheetId']
    file_id = str(SHEET_ID)
    print(SHEET_ID)
    print('Created "%s"' % res['properties']['title'])
    SHEETS.spreadsheets().values().update(spreadsheetId=SHEET_ID,
                                          range='A1', body=data, valueInputOption='RAW').execute()
    # print('Wrote data to Sheet:')
    #rows = SHEETS.spreadsheets().values().get(spreadsheetId=SHEET_ID,
    #                                        range='Sheet1').execute().get('values', [])


@app.route('/weekly_attendance/<string:training_group>')
@is_logged_in_super_admin
def weekly_attendance(training_group):
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    conn, cur = connection()
    export_to_sheets('Attendance [%s] [%s]' % (training_group, time.ctime()), get_weekly_attendance(training_group))
    cur.execute('DELETE FROM weekly_attendance')
    conn.commit()
    conn.close()
    return redirect(url_for('archive_page'))


def get_weekly_attendance(training_group):
    conn, cur = connection()
    # make selection between all the training groups or just one
    if training_group == 'all':
        return get_end_attendance()
        #cur.execute('SELECT * FROM swimmers')
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
            # checks if percent == null
            percent = None
            cur.execute(
                'INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, 0)',
                (int(swimmerID), swimmerName, percent, float(swimmerTotal)))
            conn.commit()
        else:
            # gets attendance from db
            attendance = cur.fetchall()
            attendanceTotal = attendance[0]['total']
            # make sure attendance total does not = 0 so no divide by 0 error
            if attendanceTotal == 0:
                percent = None
                cur.execute(
                    'INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, 0)',
                    (int(swimmerID), swimmerName, percent, float(swimmerTotal)))
                conn.commit()
            else:
                # calculates percent if attendance total doesn't equal 0
                percent = swimmerTotal / attendanceTotal * 100
                cur.execute(
                    'INSERT INTO weekly_attendance(id, name, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s)',
                    (int(swimmerID), swimmerName, float(percent), float(swimmerTotal), float(attendanceTotal)))
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
        for key, value in row.items():
            if key == 'percent':
                tmp.append(str(value) + '%')
            else:
                tmp.append(value)
        tmp = tmp[::-1]
        newRows.append(tmp)
        tmp = []
    newRows.insert(0, FIELDS)
    data = {'values': [row[0:] for row in newRows]}
    #flash(data)
    cur.execute(
        'INSERT INTO weekly_attendance_history(id, name, percent, total, attendance_total) SELECT id, name, percent, total, attendance_total FROM weekly_attendance')
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
    export_to_sheets('End of season attendance [%s]' % time.ctime(), get_end_attendance())
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
            cur.execute(
                'INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, 0)',
                (int(swimmerID), swimmerName, swimmerGroup, percent, float(swimmerTotal)))
            conn.commit()
        else:
            attendance = cur.fetchall()
            attendanceTotal = attendance[0]['total']
            if attendanceTotal == 0:
                percent = None
                cur.execute(
                    'INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, 0)',
                    (int(swimmerID), swimmerName, swimmerGroup, percent, float(swimmerTotal)))
                conn.commit()
            else:
                percent = swimmerTotal / attendanceTotal * 100
                cur.execute(
                    'INSERT INTO season_attendance(id, name, training_group, percent, total, attendance_total) VALUES(%s, %s, %s, %s, %s, %s)',
                    (int(swimmerID), swimmerName, swimmerGroup, float(percent), float(swimmerTotal),
                     float(attendanceTotal)))
                conn.commit()

    groupList = []
    for i in range(len(groups)):
        groupList.append(groups[i]['training_group'])

    totalRows = []
    # top of the spreadsheet
    FIELDS = ('Name', 'Percent', 'Total', 'A_Total')
    for group in groupList:
        cur.execute('SELECT name, percent, total, attendance_total FROM season_attendance WHERE training_group = %s',
                    [group])
        rows = cur.fetchall()
        rows = list(rows)
        newRows = []
        for row in rows:
            tmp = []
            for key, value in row.items():
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
        # newRows.insert(1, spacer)
        newRows.insert(1, FIELDS)
        for i in range(2, 6):
            newRows.append(spacer)

        totalRows.append(newRows)
        newRows = []

    finalRows = []
    for i in range(len(totalRows)):
        for row in totalRows[i]:
            finalRows.append(row)

    # data = {'values': [row[0:] for row in finalRows]}
    data = {'values': [row for row in finalRows]}
    cur.execute('DELETE FROM season_attendance')
    conn.commit()
    conn.close()
    return data


def get_access_codes():
    conn, cur = connection()
    cur.execute('SELECT name, code FROM swimmers ORDER BY name ASC')
    swimmer_codes = cur.fetchall()
    FIELDS = ('Name', 'Access Code')
    data_list = []
    for i in range(len(swimmer_codes)):
        data_list.append([swimmer_codes[i]['name'], swimmer_codes[i]['code']])
    data_list.insert(0, FIELDS)
    data = {'values': [row for row in data_list]}
    return data


@app.route('/print_access_codes')
@is_logged_in_super_admin
def print_access_codes():
    # connects to google if not connected already
    if 'credentials' not in session:
        return redirect(url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    export_to_sheets('Swimmer Access Codes', get_access_codes())
    return redirect(url_for('archive_page'))


# comment out this when on local machine
if __name__ == '__main__':
    app.run(debug=True)

# comment in this when pushing to webserver
# app.secret_key = str(os.urandom(24))
