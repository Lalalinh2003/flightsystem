from flask import Flask, render_template, redirect, url_for, request, flash
from urllib.parse import quote
from sqlalchemy import Column, Integer, String
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_admin.contrib.sqla import ModelView
from wtforms import FloatField, SelectField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

flightapp = Flask(__name__)

#==========================
#==========================
# MySQL Configuration
flightapp.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/flight_management_system' % quote('')
flightapp.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
flightapp.config['SECRET_KEY'] = 'your-secret-key'
db = SQLAlchemy(flightapp)

#==========================
#==========================
login_manager = LoginManager()
login_manager.init_app(flightapp)
login_manager.login_view = 'login'

# callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#==========================
#==========================
# Duong dan den trang chu
@flightapp.route("/")
def home():
    return render_template("home.html", current_user=current_user)

@flightapp.route("/logout")
def logout():
    logout_user()
    return redirect('/')

# Duong dan den trang dang nhap
@flightapp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        #print(username + " - " + password)
        #user = User.query.filter(username = username, password = password).first()
        user = User.query.filter_by(username = username, password = password).first()
        print(user)

        if user:
            login_user(user=user)
            position = user.employee.position
            if position == 'administrators':
                return redirect("/admin")
            else:
                return redirect("/book_tickets")
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng!')
            return redirect(url_for('login'))            
        
    if request.method == 'GET':
        if current_user.is_authenticated:
            position = current_user.employee.position
            if position == 'administrators':
                return redirect(url_for('admin'))
            elif position == 'staff':
                return redirect("/book_tickets")
            else:
                return redirect("/")
        else:
            return render_template("login.html", current_user=current_user)

# Duong dan den trang dat ve
@flightapp.route("/book_tickets")
#@login_required
def book_tickets():
    return render_template("book_tickets.html", current_user=current_user)

#==========================
#==========================
class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = Column(db.Integer, primary_key=True, autoincrement=True)
    active = Column(db.Boolean, default=True)
    username = Column(db.String(50), nullable=False)
    password = Column(db.String(50), nullable=False)

    employee = db.relationship('Employee', backref='user', uselist=False)

    def __str__(self):
        return f"User(id='{self.id}', active={self.active}, username={self.username}, password={self.password}, position={self.employee.position})"

class Employee(db.Model):
    __tablename__ = 'employee'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    #user = db.relationship('User', foreign_keys=[user_id])

class Airport(db.Model):
    __tablename__ = 'airport'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(10), nullable=False, unique=True)
    location = db.Column(db.String(120), nullable=False)

class AirportModelView(AuthenticatedView):
    can_create = True
    can_edit = True
    can_delete = True
    column_list = ['id', 'name', 'code', 'location']
    form_columns = ['name', 'code', 'location']
    column_searchable_list = ['name', 'code', 'location']
    column_filters = ['name', 'code', 'location']
    page_size = 50    

class Route(db.Model):
    __tablename__ = 'route'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    origin_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    distance = db.Column(db.Float, nullable=False)

    origin = db.relationship('Airport', foreign_keys=[origin_id])
    destination = db.relationship('Airport', foreign_keys=[destination_id])

class RouteForm(FlaskForm):
    origin = SelectField('Sân bay xuất phát', validators=[DataRequired()], coerce=int)
    destination = SelectField('Sân bay đích', validators=[DataRequired()], coerce=int)
    distance = FloatField('Khoảng Cách', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(RouteForm, self).__init__(*args, **kwargs)
        self.origin.choices = [(airport.id, airport.name) for airport in Airport.query.all()]
        self.destination.choices = [(airport.id, airport.name) for airport in Airport.query.all()]

class RouteModelView(AuthenticatedView):
    can_create = True
    can_edit = True
    can_delete = True
    column_list = ['id', 'origin.name', 'destination.name', 'distance']
    #form_columns = ['origin_id', 'destination_id', 'distance']
    form = RouteForm
    column_searchable_list = ['origin_id', 'destination_id', 'distance']
    column_filters = ['origin_id', 'destination_id', 'distance']
    column_labels = {
        'origin.name': 'Sân bay xuất phát',
        'destination.name': 'Sân bay đích',    
        'distance': 'Khoảng Cách'
    }       
    page_size = 50   

    def edit_form(self, obj):
        form = super(RouteModelView, self).edit_form(obj=obj)
        form.origin.default = obj.origin.id
        form.destination.default = obj.destination.id
        form.distance.default = obj.distance
        form.process()
        return form

class Flight(db.Model):
    __tablename__ = 'flight'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    num_seats_class_1 = db.Column(db.Integer, nullable=False)
    num_seats_class_2 = db.Column(db.Integer, nullable=False)
    available_seats_class_1 = db.Column(db.Integer, nullable=False)
    available_seats_class_2 = db.Column(db.Integer, nullable=False)
    price_seat_class_1 = db.Column(db.Float, nullable=False)
    price_seat_class_2 = db.Column(db.Float, nullable=False)

    route = db.relationship('Route', foreign_keys=[route_id])
    #transit_flights = db.relationship('TransitFlights', backref='flight', lazy=True)

class TransitFlight(db.Model):
    __tablename__ = 'transit_flight'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    airport_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=False)

class TransitFlights(db.Model):
    __tablename__ = 'transit_flights'
    __table_args__ = {'mysql_engine':'InnoDB'}
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), primary_key=True)
    transit_flight_id = db.Column(db.Integer, db.ForeignKey('transit_flight.id'), primary_key=True)

    flight = db.relationship('Flight', foreign_keys=[flight_id])
    transit_flight = db.relationship('TransitFlight', foreign_keys=[transit_flight_id])

class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/')
    
    def is_accessible(self):
        return current_user.is_authenticated    

class AdminView(AdminIndexView):
    #name='NOT HOME'
    #@expose('/')
    #def index(self):
    #    return redirect('/admin')
    
    def is_accessible(self):
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))    
#==========================
#==========================
with flightapp.app_context():
    db.drop_all()
    db.create_all()

    users = [
        User(id="1", username='ndtuan', password='12345!fra',active=True),
        User(id="2", username='ltkhoa', password='12345!fra', active=True)
    ]
    db.session.add_all(users)
    db.session.commit()

    employees = [
        Employee(full_name='Nguyễn Đức Tuấn', position='administrators', user_id='1'),
        Employee(full_name='Lê Thị Kim Hoa', position='staff', user_id='2')
    ]
    db.session.add_all(employees)
    db.session.commit()

    airports = [
        Airport(code='HAN', name='Hà Nội', location='Địa chỉ 1'),
        Airport(code='HPH', name='Hải Phòng', location='Địa chỉ 2'),
        Airport(code='THD', name='Thanh Hóa', location='Địa chỉ 3'),
        Airport(code='VDO', name='Vân Đồn', location='Địa chỉ 4'),
        Airport(code='DIN', name='Điện Biên', location='Địa chỉ 5'),
        Airport(code='DAD', name='Đà Nẵng', location='Địa chỉ 6'),
        Airport(code='HUI', name='Huế', location='Địa chỉ 7'),
        Airport(code='VII', name='Vinh', location='Địa chỉ 8'),
        Airport(code='VDH', name='Đồng Hới', location='Địa chỉ 9'),
        Airport(code='TBB', name='Tuy Hòa', location='Địa chỉ 10'),
        Airport(code='VCL', name='Chu Lai', location='Địa chỉ 11'),
        Airport(code='TMK', name='Tam Kỳ', location='Địa chỉ 12'),
        Airport(code='SGN', name='Hồ Chí Minh', location='Địa chỉ 13'),
        Airport(code='CXR', name='Nha Trang', location='Địa chỉ 14'),
        Airport(code='DLI', name='Đà Lạt', location='Địa chỉ 15'),
        Airport(code='UIH', name='Qui Nhơn', location='Địa chỉ 16'),
        Airport(code='PQC', name='Phú Quốc', location='Địa chỉ 17'),
        Airport(code='VCA', name='Cần Thơ', location='Địa chỉ 18'),
        Airport(code='BMV', name='Ban Mê Thuột', location='Địa chỉ 19'),
        Airport(code='PXU', name='Pleiku', location='Địa chỉ 20'),
        Airport(code='VCS', name='Côn Đảo', location='Địa chỉ 21'),
        Airport(code='VKG', name='Rạch Giá', location='Địa chỉ 22'),
        Airport(code='CAH', name='Cà Mau', location='Địa chỉ 23'),
    ]
    db.session.add_all(airports)
    db.session.commit()

    routes = [
        Route(origin_id='1', destination_id='13', distance='1704.2'),
        Route(origin_id='13', destination_id='1', distance='1704.2'),
        Route(origin_id='6', destination_id='7', distance='92.9'),
        Route(origin_id='7', destination_id='6', distance='92.9'),
    ]
    db.session.add_all(routes)
    db.session.commit()

#==========================
#==========================
admin = Admin(flightapp, name='Quản Lý', template_mode='bootstrap3', index_view=AdminView(name='Trang Chủ'))
admin.add_view(AirportModelView(Airport, db.session, name='Sân Bay'))
admin.add_view(RouteModelView(Route, db.session, name='Tuyến Bay'))
admin.add_view(LogoutView(name="Đăng xuất"))
#==========================
#==========================
if __name__ == '__main__':
    flightapp.run(debug=True)
