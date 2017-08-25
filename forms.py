from wtforms import Form, StringField, PasswordField, SelectField, IntegerField, BooleanField, DecimalField, validators

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
    group = SelectField('Group', choices=[('marlin_teal', 'Marlin Teal'), ('marlin_black', 'Marlin Black'), ('wave_teal', 'Wave Teal'), ('wave_black', 'Wave Black'), ('wave_gold', 'Wave Gold'), ('senior_prep', 'Senior Prep'), ('senior', 'Senior')])

class JobForm(Form):
    name = StringField('Name', [validators.Length(min = 1, max = 50)])
    minimum = IntegerField('Minimum people required')
    difficulty = SelectField('Difficulty level', choices = [('1', '1'), ('2','2'), ('3','3')])
    dump = BooleanField('Dump rest in this job')

class AttendanceForm(Form):
    amount = DecimalField('Amount', [validators.DataRequired()], places = 2)
    group = SelectField('Group', choices=[('marlin_teal', 'Marlin Teal'), ('marlin_black', 'Marlin Black'), ('wave_teal', 'Wave Teal'), ('wave_black', 'Wave Black'), ('wave_gold', 'Wave Gold'), ('senior_prep', 'Senior Prep'), ('senior', 'Senior')])
