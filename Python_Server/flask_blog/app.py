import os

from flask import Flask, render_template_string, request, flash, render_template, url_for, redirect, session, copy_current_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, auth_required, hash_password
from flask_security.models import fsqla_v3 as fsqla
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import create_engine, ForeignKey, String, update, bindparam, MetaData, insert, update
from typing import List
from typing import Optional
import time
import threading
from threading import Lock
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
import sys
import logging
import json

logging.basicConfig(level=logging.DEBUG)




# Create app
app = Flask(__name__)
#DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER,pw=POSTGRES_PW,url=POSTGRES_URL,db=POSTGRES_DB)
app.config['DEBUG'] = True

# Generate a nice key using secrets.token_urlsafe()
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", 'pf9Wkove4IKEAXvy-cQkeDPhv9Cb3Ag-wyJILbq_dFw')
# Generate a good salt for password hashing using: secrets.SystemRandom().getrandbits(128)
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get("SECURITY_PASSWORD_SALT", '146585145368132386173505678016728509634')

# have session and remember cookie be samesite (flask/flask_login)
app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
app.config["SESSION_COOKIE_SAMESITE"] = "strict"

# Use an in-memory db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
#app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
# As of Flask-SQLAlchemy 2.4.0 it is easy to pass in options directly to the
# underlying engine. This option makes sure that DB connections from the
# pool are still valid. Important for entire application since
# many DBaaS options automatically close idle connections.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

socketio = SocketIO(app, async_mode=async_mode, logger=True, engineio_logger=True)

# Create database connection object
db = SQLAlchemy(app)

# Define models
fsqla.FsModels.set_db_info(db)

#### begin new section

#create engine
engine = db.create_engine("sqlite://", echo=True)
#engine = db.create_engine(DB_URL, echo=True)
meta = db.MetaData()
thread_lock = Lock()
thread = None

#class Base(DeclarativeBase):
#    pass

'''
# database name
hotel = db.Table(
    'hotel',                                        
    meta,                                    
    db.Column('name', db.String, primary_key=True),                  
    db.Column('length_booked', db.Integer),                
)
'''

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    length_booked = db.Column(db.Integer)
  
    def __init__(self, name, length_booked):
        self.name = name
        self.length_booked = length_booked

    def __repr__(self):
        return '<Hotel %r>' % self.name

'''
def init_db(): 
    db.create_all()

    db.session.add(Hotel('Marriott', 0))
    db.session.add(Hotel('Hyatt',0))
    db.session.commit()

    hotels = Hotel.query.all()
    print(hotels)
'''



#meta.create_all(engine)

'''
with engine.connect() as conn:
    conn.execute(
        insert(hotel),
        [
            {"name": "Marriott", "length_booked": 0},
            {"name": "Hyatt", "length_booked": 0},
        ]
)
'''

def hotelquery(): 
    hotelchoices = [str(i) for i in db.session.query(Hotel.name)]
    striphotelchoices = []
    for value in hotelchoices: 
        striphotelchoices.append(value.strip("',()"))
    hotelchoices = striphotelchoices

    hotelbookings = [str(i) for i in db.session.query(Hotel.length_booked)]
    striphotelbookings = []
    for value in hotelbookings: 
        striphotelbookings.append(value.strip("',()"))
    hotelbookings = striphotelbookings

    return(hotelchoices, hotelbookings)
    
# Create the profile table
#meta.create_all(engine)

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count})


@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.event
def reader_ping():
    hotelchoices, hotelbookings = hotelquery()
    #hotelDB = Hotel.query.all()
    data = dict(zip(hotelchoices,hotelbookings))
    data = json.dumps(data)
    JS_data = json.loads(data)
    emit('reader_data', JS_data)



@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})




def maintain_booking(hname, booktime):
    time.sleep(booktime)
    hotelname = Hotel.query.filter_by(name=hname).first()
    hotelname.length_booked = 0
    db.session.commit()
    print("test to console",file=sys.stderr)


  

##### end new section

class Role(db.Model, fsqla.FsRoleMixin):
    pass

class User(db.Model, fsqla.FsUserMixin):
    pass



# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Views
@app.route("/")
def index():
    #db_name = db.engine.url.database
    return render_template('index.html')

@app.route("/reader")
def reader():
    return render_template('reader.html')

@app.route('/create', methods=('GET', 'POST'))
@auth_required()
def create():
    
    hotelchoices = hotelquery()[0]
    
    if request.method == 'POST':
        
        #### get to work with auth-required, also get to work as a query of database
        #return redirect(url_for('index'))
        #booking = request.form.get("hname")
        #time = request.form.get("hnumber")
        result = request.form
        #return redirect(url_for('index')
        if not result:
            flash('Hotel Name is required!')
        else:
            booking = result.get("hotelname")
            length_booked = result.get("hnumber")
            
            #hotelname = Hotel.query.filter_by(name=booking).first()
            if booking in hotelchoices: 
                hotelname = Hotel.query.filter_by(name=booking).first()
                hotelname.length_booked = length_booked
                db.session.commit()

                # now we wait for the length of the booking, then make hotel available again
                # using a separate thread for this so that the webpage will return result.html and not just wait for the booking to complete
                threading.Thread(target=maintain_booking, args=(hotelname,int(length_booked)))
                


            else: 
                flash('Hotel not in system')

            return render_template("result.html", result=result)
        
    
    return render_template('create.html', hotelchoices = hotelchoices)
  


# one time setup
with app.app_context():
    # Create User to test with
    db.create_all()
    if not security.datastore.find_user(email="test@me.com"):
        security.datastore.create_user(email="test@me.com", password=hash_password("password"))
    db.session.commit()

    db.session.add(Hotel('Marriott', 0))
    db.session.add(Hotel('Hyatt',0))
    db.session.commit()

    hotels = Hotel.query.all()
    print(hotels)

if __name__ == '__main__':
    #init_db()
    
    #create_data()
    socketio.run(app, port=8080)