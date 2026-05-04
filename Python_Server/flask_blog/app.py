import os
import random

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

logging.basicConfig(level=logging.DEBUG)


# Create app
app = Flask(__name__)
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
async_mode = threading

socketio = SocketIO(app, async_mode="threading", logger=True, engineio_logger=True)

# Create database connection object
db = SQLAlchemy(app)

# Define models
fsqla.FsModels.set_db_info(db)

#### begin new section

#create engine
engine = db.create_engine("sqlite://", echo=True)
meta = db.MetaData()
thread_lock = Lock()
thread = None
reading = threading.Lock()
writing = threading.Lock()
mutex = threading.Lock()
random.seed()

lock = threading.Lock()
conditionread = threading.Condition(lock)
conditionwrite = threading.Condition(lock)
aw = 0
ww = 0
ar = 0
wr = 0
fa = 0


#Reader Writer Global Variables
activeReader = 0
activeWriter = 0
waitingReader = 0
waitingWriter = 0

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


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': waitingReader})


# Create the profile table
#meta.create_all(engine)

def r():
    socketio.sleep(random.randint(3,10))
    global activeReader
    with reading:
        with mutex:
            activeReader += 1
            socketio.emit('my_response', {'data': 'Server generated event', 'count': activeReader})
            if activeReader == 1:
                writing.acquire()
    socketio.sleep(random.randint(3, 10))
    with mutex:
        activeReader -= 1
        if activeReader == 0:
            writing.release()


def readers():
   global activeWriter, waitingWriter, activeReader, waitingReader
   socketio.sleep(random.randint(3,10))
   with lock:
       while (activeWriter + waitingWriter) > 0:
           waitingReader += 1
          # socketio.emit('my_response', {'data': 'Read wait', 'count': waitingReader})
           conditionread.wait()
           waitingReader -= 1
       activeReader += 1
   socketio.emit('my_response', {'data': 'Reading', 'count': activeReader})
   socketio.sleep(random.randint(3,10))
   with lock:
       activeReader -= 1
       if activeReader == 0 and waitingWriter > 0:
           conditionwrite.notify()

def writers():
    global activeWriter, waitingWriter, activeReader, waitingReader
    socketio.sleep(random.randint(3,10))
    with lock:
        while (activeWriter + activeReader) > 0:
            waitingWriter += 1
            #socketio.emit('my_response', {'data': 'write wait', 'count': waitingWriter})
            conditionwrite.wait()
            waitingWriter -= 1
        activeWriter += 1
    socketio.emit('my_response', {'data': 'writer write', 'count': activeWriter})
    socketio.sleep(random.randint(3,10))
    with lock:
        activeWriter -= 1
        if waitingWriter > 0:
            conditionwrite.notify()
        else:
            conditionread.notify_all()


@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})




@socketio.event
def connect():
    '''
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    '''
    for _ in range(10):
        socketio.start_background_task(readers)

    for _ in range(5):
        socketio.start_background_task(writers)

    emit('my_response', {'data': 'Connected', 'count': 0})




def maintain_booking(hotelname, length_booked):
    time.sleep(length_booked)
    hotelname.length_booked = 0
    db.session.commit()
    #print("finished thread\n",file=sys.stderr)
  

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
    return render_template('index.html')

@app.route("/reader")
def reader():
    return render_template('reader.html')

@app.route('/create', methods=('GET', 'POST'))
@auth_required()
def create():
    
    hotelchoices = [str(i) for i in db.session.query(Hotel.name)]
    striphotelchoices = []
    for value in hotelchoices: 
        striphotelchoices.append(value.strip("',()"))
    hotelchoices = striphotelchoices
    #for hotelchoice in hotelchoices: 
    #    print(hotelchoice.name)
    
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
                print("test to console",file=sys.stderr)


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
    socketio.run(app)