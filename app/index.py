from datetime import datetime, time, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash
from urllib.parse import quote
from sqlalchemy import Column, Integer, String, or_
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_admin.contrib.sqla import ModelView
from wtforms import DateField, FloatField, SelectField, StringField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from sqlalchemy import and_

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
@flightapp.route("/book_tickets", methods=['GET', 'POST'])
#@login_required
def book_tickets():
    airport_origin = request.args.get('airport_origin')
    airport_destination = request.args.get('airport_destination')
    airport_departure_date = request.args.get('airport_departure_date')

    twelve_hours_ago = datetime.now() - timedelta(hours=10)
    print(twelve_hours_ago)
    flights = Flight.query.filter(and_(Flight.departure_time >= twelve_hours_ago), or_(Flight.available_seats_class_1 > 0, Flight.available_seats_class_2 > 0)).all()    

    formSearchFlight = FormSearchFlight()
    if formSearchFlight.validate_on_submit():
        origin_id = formSearchFlight.origin.data
        destination_id = formSearchFlight.destination.data
        departure_date = formSearchFlight.departure_date.data
        #print(origin_id)
        #print(destination_id)
        #print(departure_date)
        
        # Do something with the search parameters
        #flights = Flight.query.filter_by(origin_id=origin_id, destination_id=destination_id).all()
        flights = Flight.query.join(Route, Flight.route_id == Route.id).filter(Route.origin_id==origin_id, Route.destination_id==destination_id, Flight.departure_time >= twelve_hours_ago, or_(Flight.available_seats_class_1 > 0, Flight.available_seats_class_2 > 0)).all()

    return render_template("book_tickets.html", current_user=current_user, flights=flights, formSearchFlight=formSearchFlight)

@flightapp.route("/buy_tickets", methods=['POST'])
def buy_tickets():
    if request.method == 'POST':
        #print(request.form)
        flightId = request.form['flight_id']
        flightCode = request.form['flight_code']
        routeId = request.form['route_id']
        originName = request.form['origin_name']
        destinationName = request.form['destination_name']
        departureTime = request.form['departure_time']
        arrivalTime = request.form['arrival_time']
        seatClass = request.form['seat_class']
        seatPrice = request.form['seat_price']

        return render_template('buy_tickets.html', flightId=flightId, flightCode=flightCode, routeId=routeId, originName=originName, destinationName=destinationName, departureTime=departureTime, arrivalTime=arrivalTime, seatClass=seatClass, seatPrice=seatPrice)
    
    return redirect(url_for('book_tickets'))

@flightapp.route("/save_ticket", methods=['POST'])
def save_ticket():
    flightId = request.form['flightId']
    #flightCode = request.form['flightCode']
    #routeId = request.form['routeId']
    #originName = request.form['originName']
    #destinationName = request.form['destinationName']
    #departureTime = request.form['departureTime']
    #arrivalTime = request.form['arrivalTime']
    seatClass = request.form['seatClass']
    seatPrice = request.form['seatPrice']
    #employeeId = request.form['employeeId']

    fullName = request.form['fullName']
    identityCard = request.form['identityCard']
    phoneNumber = request.form['phoneNumber']
    address = request.form['address']
    bankNumber = request.form['bankNumber']

    #-- save customer
    customer = Customer(full_name=fullName, identity_card=identityCard, address=address, phone_number=phoneNumber, bank_number=bankNumber)
    db.session.add(customer)
    db.session.commit()
    customerId = customer.id

    #-- save ticket
    ticket = Ticket(flight_id=flightId, customer_id=customerId, employee_id=None, seat_class=seatClass, seat_price=seatPrice)
    db.session.add(ticket)
    db.session.commit()

    return redirect('/')

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

class Customer(db.Model):
    __tablename__ = 'customer'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = Column(db.String(100), nullable=False)
    identity_card = Column(db.String(20), nullable=False)
    address = Column(db.String(200), nullable=False)
    phone_number = Column(db.String(20), nullable=False)
    bank_number = Column(db.String(20), nullable=False)

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

def get_routes():
    return Route.query.all()

def get_route_pk(route):
    return route.id

def get_route_label(route):
    return f'{route.origin.name} - {route.destination.name}'

class FlightModelView(AuthenticatedView):
    can_create = True
    can_edit = True
    can_delete = True
    column_list = ['id', 'code', 'route.origin.name', 'route.destination.name', 
                   'departure_time', 'arrival_time',
                   'num_seats_class_1', 'num_seats_class_2',
                   'available_seats_class_1', 'available_seats_class_2',
                   'price_seat_class_1', 'price_seat_class_2']    
    form_columns = ['code', 'route', 
                   'departure_time', 'arrival_time',
                   'num_seats_class_1', 'num_seats_class_2',
                   'available_seats_class_1', 'available_seats_class_2',
                   'price_seat_class_1', 'price_seat_class_2']
    column_searchable_list = ['code', 'route_id', 'departure_time', 'arrival_time']
    column_filters = ['code', 'route_id', 'departure_time', 'arrival_time']
    page_size = 50       

    column_labels = {
        'route.origin.name': 'Sân bay xuất phát',
        'route.destination.name': 'Sân bay đích',
    }   

    form_args = {
        'route': {
            'label': 'Route',
            'query_factory': get_routes,
            'get_pk': get_route_pk,
            'get_label': get_route_label
        }
    }

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

class Ticket(db.Model):
    __tablename__ = 'ticket'
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    seat_class = db.Column(db.String(50), nullable=False)
    seat_price = db.Column(db.Float, nullable=False)

    flight = db.relationship('Flight', foreign_keys=[flight_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    employee = db.relationship('Employee', foreign_keys=[employee_id])


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

    flights = [
        Flight(code='FLY001', route_id='1', departure_time='2023-12-03 01:00:00', arrival_time='2023-12-03 03:30:00', num_seats_class_1='10', num_seats_class_2='100', available_seats_class_1='10', available_seats_class_2='100', price_seat_class_1='1000000', price_seat_class_2='100000'),
        Flight(code='FLY002', route_id='2', departure_time='2024-01-04 01:00:00', arrival_time='2024-01-04 03:30:00', num_seats_class_1='20', num_seats_class_2='200', available_seats_class_1='20', available_seats_class_2='200', price_seat_class_1='2000000', price_seat_class_2='200000'),
        Flight(code='FLY003', route_id='3', departure_time='2024-01-05 01:00:00', arrival_time='2024-01-05 03:30:00', num_seats_class_1='30', num_seats_class_2='300', available_seats_class_1='30', available_seats_class_2='300', price_seat_class_1='3000000', price_seat_class_2='300000'),
        Flight(code='FLY004', route_id='4', departure_time='2024-01-06 01:00:00', arrival_time='2024-01-06 03:30:00', num_seats_class_1='40', num_seats_class_2='400', available_seats_class_1='40', available_seats_class_2='400', price_seat_class_1='4000000', price_seat_class_2='400000'),
    ]
    db.session.add_all(flights)
    db.session.commit()    

#==========================
#==========================
admin = Admin(flightapp, name='Quản Lý', template_mode='bootstrap3', index_view=AdminView(name='Trang Chủ'))
admin.add_view(AirportModelView(Airport, db.session, name='Sân Bay'))
admin.add_view(RouteModelView(Route, db.session, name='Tuyến Bay'))
admin.add_view(FlightModelView(Flight, db.session, name='Chuyến Bay'))
admin.add_view(LogoutView(name="Đăng xuất"))

#==========================
#==========================
class FormSearchFlight(FlaskForm):
    with flightapp.app_context():
        origin = SelectField('Origin', choices=[(airport.id, airport.name) for airport in Airport.query.all()], validators=[DataRequired()])
        destination = SelectField('Destination', choices=[(airport.id, airport.name) for airport in Airport.query.all()], validators=[DataRequired()])
        departure_date = DateField('Departure date', format='%Y-%m-%d', validators=[DataRequired()])

#==========================
#==========================
if __name__ == '__main__':
    flightapp.run(debug=True)
