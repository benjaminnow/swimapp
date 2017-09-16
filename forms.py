from wtforms import Form, StringField, PasswordField, SelectField, IntegerField, BooleanField, DecimalField, TextField, validators
from db import *


def get_groups():
    conn, cur = connection()
    cur.execute('SELECT training_group FROM set_attendance')
    groups = cur.fetchall()
    choice_list = []
    for i in range(len(groups)):
        choice_list.append((groups[i]['training_group'], groups[i]['training_group']))
    return choice_list

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min = 1, max = 50)])
    username = StringField('Username', [validators.Length(min = 3, max = 25)])
    email = StringField('Email', [validators.Length(min = 6, max = 50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message = 'Passwords do not match')
    ])
    confirm = PasswordField('Confirm password')
    access_code = PasswordField('Access Code for swimmers - leave blank if you are a coach')
    admin_code = PasswordField('Admin password - If you are an admin, enter your code here. If not, leave it blank.')

class SwimmerForm(Form):
    name = StringField('Name', [validators.Length(min = 1)])
    group = SelectField('Group', choices = get_groups())

class JobForm(Form):
    name = StringField('Name', [validators.Length(min = 1, max = 50)])
    minimum = IntegerField('Minimum people required')
    difficulty = SelectField('Difficulty level', choices = [('1', '1'), ('2','2'), ('3','3')])
    dump = BooleanField('Dump rest in this job')

class AttendanceForm(Form):
    amount = DecimalField('Amount', [validators.DataRequired()], places = 2)
    group = SelectField('Group', choices = get_groups())

class GroupForm(Form):
    name = StringField('Name', [validators.Length(min = 1, max = 50)])

class QuoteForm(Form):
    body = TextField('Quote', [validators.Length(min = 1)])
    author = StringField('Author', [validators.Length(min = 1)])

class RemoveAttendanceForm(Form):
    amount = DecimalField('Amount', [validators.DataRequired()], places=2)

class CustomAmount(Form):
    amount = DecimalField('Amount', [validators.DataRequired()], places=2)

class DefaultValue(Form):
    amount = DecimalField('Default Amount', [validators.DataRequired()], places=2)
    group = SelectField('Group', choices = get_groups())

class DefaultGroup(Form):
    group = SelectField('Group', choices = get_groups())
