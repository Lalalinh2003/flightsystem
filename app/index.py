from datetime import datetime, time, timedelta
import gettext
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash
from urllib.parse import quote
from sqlalchemy import Column, Integer, String, func, or_
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_admin.contrib.sqla import ModelView
from wtforms import DateField, FloatField, SelectField, StringField, HiddenField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from sqlalchemy import and_
from wtforms_sqlalchemy.fields import QuerySelectField

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
        #print(referrer = request.referrer)
        referrerPage = request.referrer.split("/")[-1]
        employeeId = request.form['employee_id']
        flightId = request.form['flight_id']
        flightCode = request.form['flight_code']
        routeId = request.form['route_id']
        originName = request.form['origin_name']
        destinationName = request.form['destination_name']
        departureTime = request.form['departure_time']
        arrivalTime = request.form['arrival_time']
        seatClass = request.form['seat_class']
        seatPrice = request.form['seat_price']

        return render_template('buy_tickets.html', flightId=flightId, flightCode=flightCode, routeId=routeId, originName=originName, destinationName=destinationName, departureTime=departureTime, arrivalTime=arrivalTime, seatClass=seatClass, seatPrice=seatPrice, employeeId=employeeId, referrerPage=referrerPage)
    
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
    employeeId = request.form['employeeId']
    fullName = request.form['fullName']
    identityCard = request.form['identityCard']
    phoneNumber = request.form['phoneNumber']
    address = request.form['address']
    bankNumber = request.form['bankNumber']
    referrerPage = request.form['referrerPage']

    if not (employeeId):
        employeeId = None    

    #-- save customer
    customer = Customer(full_name=fullName, identity_card=identityCard, address=address, phone_number=phoneNumber, bank_number=bankNumber)
    db.session.add(customer)
    db.session.commit()
    customerId = customer.id

    #-- save ticket
    ticket = Ticket(flight_id=flightId, customer_id=customerId, employee_id=employeeId, seat_class=seatClass, seat_price=seatPrice)
    db.session.add(ticket)
    db.session.commit()

    #-- update seat of flight
    flight = Flight.query.get(flightId)
    if seatClass == "Seats class 1":
        flight.available_seats_class_1 = flight.available_seats_class_1 - 1
    else:
        flight.available_seats_class_2 = flight.available_seats_class_2 - 1
    db.session.commit()

    #--
    return render_template("tickets.html", flight=flight, ticket=ticket, customer=customer, employeeId=employeeId, referrerPage=referrerPage)


@flightapp.route("/sales_tickets", methods=['GET', 'POST'])
@login_required
def sales_tickets():
    if request.method == 'GET':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
    employeeId = current_user.employee.id
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

    return render_template("sales_tickets.html", current_user=current_user, flights=flights, formSearchFlight=formSearchFlight, employeeId=employeeId)

@flightapp.route("/tickets", methods=['POST'])
def tickets():
    if request.method == 'POST':
        #print(referrer = request.referrer)
        referrerPage = request.referrer.split("/")[-1]
        employeeId = request.form['employee_id']
        flightId = request.form['flight_id']
        flightCode = request.form['flight_code']
        routeId = request.form['route_id']
        originName = request.form['origin_name']
        destinationName = request.form['destination_name']
        departureTime = request.form['departure_time']
        arrivalTime = request.form['arrival_time']
        seatClass = request.form['seat_class']
        seatPrice = request.form['seat_price']

        return render_template('tickets.html', flightId=flightId, flightCode=flightCode, routeId=routeId, originName=originName, destinationName=destinationName, departureTime=departureTime, arrivalTime=arrivalTime, seatClass=seatClass, seatPrice=seatPrice, employeeId=employeeId, referrerPage=referrerPage)
    
    return redirect(url_for('book_tickets'))

@flightapp.route("/report", methods=['GET', 'POST'])
@login_required
def report():
    now=datetime.now()

    if request.method == 'POST':
        month = request.form['month']
        year = request.form['year']
    else:
        month = now.strftime("%m")   
        year = now.strftime("%Y")
    

    # Tạo bí danh cho bảng Airport
    airport_alias_1 = db.aliased(Airport)
    airport_alias_2 = db.aliased(Airport)

    #-- SELECT * FROM `flight` f INNER JOIN `ticket` t ON f.id = t.flight_id WHERE `departure_time` LIKE '2024-01%' ORDER BY `departure_time` ASC
    #-- SELECT f.route_id, sum(t.seat_price) FROM `flight` f INNER JOIN `ticket` t ON f.id = t.flight_id WHERE `departure_time` LIKE '2024-01%' group by(f.route_id)   
    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") 
    revenue_by_route = db.session.query(Flight.route_id, airport_alias_1.name, airport_alias_2.name, func.sum(Ticket.seat_price)).\
        join(Ticket, Flight.id == Ticket.flight_id).\
        join(Route, Flight.route_id == Route.id).\
        join(airport_alias_1, Route.origin_id == airport_alias_1.id).\
        join(airport_alias_2, Route.destination_id == airport_alias_2.id).\
        filter(db.extract('year', Flight.departure_time) == year, db.extract('month', Flight.departure_time) == month).\
        group_by(Flight.route_id).all()
    # In nội dung truy vấn
    #print(revenue_by_route.statement)
    print(revenue_by_route)


    flights_by_route = db.session.query(Flight.route_id, func.count(Flight.id)).\
        filter(db.extract('year', Flight.departure_time) == year, db.extract('month', Flight.departure_time) == month).\
        group_by(Flight.route_id).all()
    print("CCCCCCCCCCCCCCCCCCCCCC")
    #total_revenue = sum(revenue for _, _, _, revenue in revenue_by_route)
    total_revenue = sum(t[-1] for t in revenue_by_route)
    print("DDDDDDDDDDDDDDDDDDDDDDDDD")
    # Tính toán tỷ lệ doanh thu theo route
    report_data = []
    for route_id, airport_origin_name, airport_destination_name, revenue in revenue_by_route:
        flights = next((flights for route, flights in flights_by_route if route == route_id), 0)
        revenue_rate = (revenue / total_revenue) * 100 if total_revenue > 0 else 0
        report_data.append((route_id, airport_origin_name, airport_destination_name, revenue, flights, revenue_rate))

    return render_template('report.html', report_data=report_data, total_revenue=total_revenue, month=int(month), year=int(year), now=now)
    #return render_template('report.html', total_seat_price=total_seat_price, total_flights=total_flights, route_percentages=route_percentages, now=now)
    #return render_template('report.html', month=month, year=year, route_prices=route_prices, now=now)

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
    origin = QuerySelectField('Sân bay xuất phát', query_factory=lambda: Airport.query.all(), get_label='name', validators=[DataRequired()])
    destination = QuerySelectField('Sân bay đích', query_factory=lambda: Airport.query.all(), get_label='name', validators=[DataRequired()])
    distance = FloatField('Khoảng Cách', validators=[DataRequired()])
    #================================
    """
    with flightapp.app_context():
        origin = SelectField('Origin Airport', coerce=int, choices=[(airport.id, airport.name) for airport in Airport.query.all()])
        destination = SelectField('Destination Airport', coerce=int, choices=[(airport.id, airport.name) for airport in Airport.query.all()])
        distance = FloatField('Distance')    
    """        
    #================================
    """
    routeId = HiddenField(validators=[DataRequired()])
    origin = SelectField('Sân bay xuất phát', validators=[DataRequired()], coerce=int)
    destination = SelectField('Sân bay đích', validators=[DataRequired()], coerce=int)
    distance = FloatField('Khoảng Cách', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(RouteForm, self).__init__(*args, **kwargs)
        self.origin.choices = [(airport.id, airport.name) for airport in Airport.query.all()]
        self.destination.choices = [(airport.id, airport.name) for airport in Airport.query.all()]
    """

class RouteModelView(AuthenticatedView):
    can_create = True
    can_edit = True
    can_delete = True
    column_list = ['id', 'origin.name', 'destination.name', 'distance']
    #form_columns = ['origin_id', 'destination_id', 'distance']
    column_searchable_list = ['origin_id', 'destination_id', 'distance']
    column_filters = ['origin_id', 'destination_id', 'distance']
    column_labels = {
        'origin.name': 'Sân bay xuất phát',
        'destination.name': 'Sân bay đích',    
        'distance': 'Khoảng Cách'
    }
    page_size = 50   

    form = RouteForm

    """        
    def edit_form(self, obj):
        try:
            print(obj)
            form = super(RouteModelView, self).edit_form(obj)
            form.routeId.data = obj.id
            form.origin.data = obj.origin_id
            form.destination.data = obj.destination_id
            form.distance.data = obj.distance
            return form 
        except Exception as ex:
            print(ex)
            flash(gettext('Failed to edit product. %(error)s', error=str(ex)), 'error')
    

    def on_model_change(self, form, model, is_created):
        db.session.add(model)
        db.session.commit()
    """           

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
        Route(origin_id='1', destination_id='2', distance='1200.2'),
        Route(origin_id='1', destination_id='3', distance='1300.3'),
        Route(origin_id='1', destination_id='4', distance='1400.4'),
        Route(origin_id='1', destination_id='5', distance='1500.5'),
        Route(origin_id='1', destination_id='6', distance='1600.6'),
        Route(origin_id='1', destination_id='7', distance='1700.7'),
        Route(origin_id='1', destination_id='8', distance='1800.8'),
        Route(origin_id='1', destination_id='9', distance='1900.9'),
    ]
    db.session.add_all(routes)
    db.session.commit()

    flights = [
        Flight(code='FLY001', route_id='1', departure_time='2023-12-01 01:00:00', arrival_time='2023-12-01 02:30:00', num_seats_class_1='10', num_seats_class_2='100', available_seats_class_1='0', available_seats_class_2='90', price_seat_class_1='1000000', price_seat_class_2='100000'),
        Flight(code='FLY002', route_id='2', departure_time='2023-12-02 02:00:00', arrival_time='2023-01-02 03:30:00', num_seats_class_1='20', num_seats_class_2='200', available_seats_class_1='20', available_seats_class_2='200', price_seat_class_1='2000000', price_seat_class_2='200000'),
        Flight(code='FLY003', route_id='3', departure_time='2023-12-03 03:00:00', arrival_time='2023-01-03 04:30:00', num_seats_class_1='30', num_seats_class_2='300', available_seats_class_1='30', available_seats_class_2='300', price_seat_class_1='3000000', price_seat_class_2='300000'),
        Flight(code='FLY004', route_id='4', departure_time='2023-12-04 04:00:00', arrival_time='2023-01-04 05:30:00', num_seats_class_1='40', num_seats_class_2='400', available_seats_class_1='40', available_seats_class_2='400', price_seat_class_1='4000000', price_seat_class_2='400000'),
        Flight(code='FLY005', route_id='5', departure_time='2023-12-05 05:00:00', arrival_time='2023-01-05 06:30:00', num_seats_class_1='50', num_seats_class_2='500', available_seats_class_1='50', available_seats_class_2='500', price_seat_class_1='5000000', price_seat_class_2='500000'),
        Flight(code='FLY006', route_id='6', departure_time='2023-12-06 06:00:00', arrival_time='2023-01-06 07:30:00', num_seats_class_1='60', num_seats_class_2='600', available_seats_class_1='60', available_seats_class_2='600', price_seat_class_1='6000000', price_seat_class_2='600000'),
        Flight(code='FLY007', route_id='7', departure_time='2023-12-07 07:00:00', arrival_time='2023-01-07 08:30:00', num_seats_class_1='70', num_seats_class_2='700', available_seats_class_1='70', available_seats_class_2='700', price_seat_class_1='7000000', price_seat_class_2='700000'),
        Flight(code='FLY008', route_id='8', departure_time='2023-12-08 08:00:00', arrival_time='2023-01-08 09:30:00', num_seats_class_1='80', num_seats_class_2='800', available_seats_class_1='80', available_seats_class_2='800', price_seat_class_1='8000000', price_seat_class_2='800000'),
        Flight(code='FLY009', route_id='9', departure_time='2023-12-09 09:00:00', arrival_time='2023-01-09 10:30:00', num_seats_class_1='90', num_seats_class_2='900', available_seats_class_1='90', available_seats_class_2='900', price_seat_class_1='9000000', price_seat_class_2='900000'),
        Flight(code='FLY010', route_id='10', departure_time='2023-12-10 10:00:00', arrival_time='2023-01-10 11:30:00', num_seats_class_1='100', num_seats_class_2='1000', available_seats_class_1='100', available_seats_class_2='1000', price_seat_class_1='10000000', price_seat_class_2='1000000'),        
        
        Flight(code='FLY011', route_id='1', departure_time='2024-01-11 01:00:00', arrival_time='2024-01-11 02:30:00', num_seats_class_1='10', num_seats_class_2='100', available_seats_class_1='0', available_seats_class_2='90', price_seat_class_1='1000000', price_seat_class_2='100000'),
        Flight(code='FLY012', route_id='2', departure_time='2024-01-12 02:00:00', arrival_time='2024-01-12 03:30:00', num_seats_class_1='20', num_seats_class_2='200', available_seats_class_1='20', available_seats_class_2='200', price_seat_class_1='2000000', price_seat_class_2='200000'),
        Flight(code='FLY013', route_id='3', departure_time='2024-01-13 03:00:00', arrival_time='2024-01-13 04:30:00', num_seats_class_1='30', num_seats_class_2='300', available_seats_class_1='30', available_seats_class_2='300', price_seat_class_1='3000000', price_seat_class_2='300000'),
        Flight(code='FLY014', route_id='4', departure_time='2024-01-14 04:00:00', arrival_time='2024-01-14 05:30:00', num_seats_class_1='40', num_seats_class_2='400', available_seats_class_1='40', available_seats_class_2='400', price_seat_class_1='4000000', price_seat_class_2='400000'),
        Flight(code='FLY015', route_id='5', departure_time='2024-01-15 05:00:00', arrival_time='2024-01-15 06:30:00', num_seats_class_1='50', num_seats_class_2='500', available_seats_class_1='50', available_seats_class_2='500', price_seat_class_1='5000000', price_seat_class_2='500000'),
        Flight(code='FLY016', route_id='6', departure_time='2024-01-16 06:00:00', arrival_time='2024-01-16 07:30:00', num_seats_class_1='60', num_seats_class_2='600', available_seats_class_1='60', available_seats_class_2='600', price_seat_class_1='6000000', price_seat_class_2='600000'),
        Flight(code='FLY017', route_id='7', departure_time='2024-01-17 07:00:00', arrival_time='2024-01-17 08:30:00', num_seats_class_1='70', num_seats_class_2='700', available_seats_class_1='70', available_seats_class_2='700', price_seat_class_1='7000000', price_seat_class_2='700000'),
        Flight(code='FLY018', route_id='8', departure_time='2024-01-18 08:00:00', arrival_time='2024-01-18 09:30:00', num_seats_class_1='80', num_seats_class_2='800', available_seats_class_1='80', available_seats_class_2='800', price_seat_class_1='8000000', price_seat_class_2='800000'),
        Flight(code='FLY019', route_id='9', departure_time='2024-01-19 09:00:00', arrival_time='2024-01-19 10:30:00', num_seats_class_1='90', num_seats_class_2='900', available_seats_class_1='90', available_seats_class_2='900', price_seat_class_1='9000000', price_seat_class_2='900000'),
        Flight(code='FLY020', route_id='10', departure_time='2024-01-20 10:00:00', arrival_time='2024-01-20 11:30:00', num_seats_class_1='100', num_seats_class_2='1000', available_seats_class_1='90', available_seats_class_2='900', price_seat_class_1='10000000', price_seat_class_2='1000000'),

        Flight(code='FLY021', route_id='1', departure_time='2024-01-21 01:00:00', arrival_time='2024-01-21 02:30:00', num_seats_class_1='5', num_seats_class_2='15', available_seats_class_1='4', available_seats_class_2='14', price_seat_class_1='5000000', price_seat_class_2='150000'),
    ]
    db.session.add_all(flights)
    db.session.commit()    

    customers = [
        Customer(full_name='Khách hàng số 001' ,identity_card='ID0001' ,address='Địa chỉ 001' ,phone_number='0000000001' ,bank_number='BANK0001' ),
        Customer(full_name='Khách hàng số 002' ,identity_card='ID0002' ,address='Địa chỉ 002' ,phone_number='0000000002' ,bank_number='BANK0002' ),
        Customer(full_name='Khách hàng số 003' ,identity_card='ID0003' ,address='Địa chỉ 003' ,phone_number='0000000003' ,bank_number='BANK0003' ),
        Customer(full_name='Khách hàng số 004' ,identity_card='ID0004' ,address='Địa chỉ 004' ,phone_number='0000000004' ,bank_number='BANK0004' ),
        Customer(full_name='Khách hàng số 005' ,identity_card='ID0005' ,address='Địa chỉ 005' ,phone_number='0000000005' ,bank_number='BANK0005' ),
        Customer(full_name='Khách hàng số 006' ,identity_card='ID0006' ,address='Địa chỉ 006' ,phone_number='0000000006' ,bank_number='BANK0006' ),
        Customer(full_name='Khách hàng số 007' ,identity_card='ID0007' ,address='Địa chỉ 007' ,phone_number='0000000007' ,bank_number='BANK0007' ),
        Customer(full_name='Khách hàng số 008' ,identity_card='ID0008' ,address='Địa chỉ 008' ,phone_number='0000000008' ,bank_number='BANK0008' ),
        Customer(full_name='Khách hàng số 009' ,identity_card='ID0009' ,address='Địa chỉ 009' ,phone_number='0000000009' ,bank_number='BANK0009' ),
        Customer(full_name='Khách hàng số 010' ,identity_card='ID0010' ,address='Địa chỉ 010' ,phone_number='0000000010' ,bank_number='BANK0010' ),
        Customer(full_name='Khách hàng số 011' ,identity_card='ID0011' ,address='Địa chỉ 011' ,phone_number='0000000011' ,bank_number='BANK0011' ),
        Customer(full_name='Khách hàng số 012' ,identity_card='ID0012' ,address='Địa chỉ 012' ,phone_number='0000000012' ,bank_number='BANK0012' ),
        Customer(full_name='Khách hàng số 013' ,identity_card='ID0013' ,address='Địa chỉ 013' ,phone_number='0000000013' ,bank_number='BANK0013' ),
        Customer(full_name='Khách hàng số 014' ,identity_card='ID0014' ,address='Địa chỉ 014' ,phone_number='0000000014' ,bank_number='BANK0014' ),
        Customer(full_name='Khách hàng số 015' ,identity_card='ID0015' ,address='Địa chỉ 015' ,phone_number='0000000015' ,bank_number='BANK0015' ),
        Customer(full_name='Khách hàng số 016' ,identity_card='ID0016' ,address='Địa chỉ 016' ,phone_number='0000000016' ,bank_number='BANK0016' ),
        Customer(full_name='Khách hàng số 017' ,identity_card='ID0017' ,address='Địa chỉ 017' ,phone_number='0000000017' ,bank_number='BANK0017' ),
        Customer(full_name='Khách hàng số 018' ,identity_card='ID0018' ,address='Địa chỉ 018' ,phone_number='0000000018' ,bank_number='BANK0018' ),
        Customer(full_name='Khách hàng số 019' ,identity_card='ID0019' ,address='Địa chỉ 019' ,phone_number='0000000019' ,bank_number='BANK0019' ),
        Customer(full_name='Khách hàng số 020' ,identity_card='ID0020' ,address='Địa chỉ 020' ,phone_number='0000000020' ,bank_number='BANK0020' ),
    ]
    db.session.add_all(customers)
    db.session.commit()    

    tickets = [
        Ticket(flight_id='1',  customer_id='1', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='2', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='3', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='4', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='5', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='6', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='7', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='8', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1',  customer_id='9', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1', customer_id='10', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='1', customer_id='11', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='12', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='13', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='14', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='15', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='16', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='17', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='18', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='19', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='1', customer_id='20', employee_id=None, seat_class='Seats class 2', seat_price='100000'),     

        Ticket(flight_id='11',  customer_id='1', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='2', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='3', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='4', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='5', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='6', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='7', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='8', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11',  customer_id='9', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11', customer_id='10', employee_id=None, seat_class='Seats class 1', seat_price='1000000'),
        Ticket(flight_id='11', customer_id='11', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='12', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='13', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='14', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='15', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='16', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='17', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='18', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='19', employee_id=None, seat_class='Seats class 2', seat_price='100000'),
        Ticket(flight_id='11', customer_id='20', employee_id=None, seat_class='Seats class 2', seat_price='100000'),     

        Ticket(flight_id='20',  customer_id='1', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='2', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='3', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='4', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='5', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='6', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='7', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='8', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20',  customer_id='9', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20', customer_id='10', employee_id=2, seat_class='Seats class 1', seat_price='10000000'),
        Ticket(flight_id='20', customer_id='11', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='12', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='13', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='14', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='15', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='16', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='17', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='18', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='19', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),
        Ticket(flight_id='20', customer_id='20', employee_id=2, seat_class='Seats class 2', seat_price='1000000'),                

        Ticket(flight_id='21', customer_id='1', employee_id=1, seat_class='Seats class 1', seat_price='5000000'),
        Ticket(flight_id='21', customer_id='2', employee_id=2, seat_class='Seats class 2', seat_price='150000'),
    ]
    db.session.add_all(tickets)
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
