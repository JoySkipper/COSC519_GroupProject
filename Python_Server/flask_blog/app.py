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
from concurrent.futures import ThreadPoolExecutor
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
import sys
import logging
import json

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

#locks and conditionals for reader and writer functions
lock = threading.Lock()
conditionread = threading.Condition(lock)
conditionwrite = threading.Condition(lock)


#Reader Writer Global Variables
activeReader = 0
activeWriter = 0
waitingReader = 0
waitingWriter = 0


# Create database model to hold all hotel data
class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    length_booked = db.Column(db.Integer)
  
    def __init__(self, name, length_booked):
        self.name = name
        self.length_booked = length_booked

    def __repr__(self):
        return '<Hotel %r>' % self.name




# reads all hotel options and their current bookings from the database

def hotelquery(hotel=""):
    with app.app_context():
        if hotel == "":
            ### CRITICAL SECTION ->
            hotelchoices = [str(i) for i in db.session.query(Hotel.name)]
            ### CRITICAL SECTION <--
            striphotelchoices = []
            for value in hotelchoices:
                striphotelchoices.append(value.strip("',()"))
            hotelchoices = striphotelchoices

            ### CRITICAL SECTION ->
            hotelbookings = [str(i) for i in db.session.query(Hotel.length_booked)]
            ### CRITICAL SECTION <--
            striphotelbookings = []
            for value in hotelbookings:
                striphotelbookings.append(value.strip("',()"))
            hotelbookings = striphotelbookings
        else:
            hotelchoices = Hotel.query.filter_by(name=hotel).first()
            hotelbookings = hotelchoices.length_booked
            #output for reader_writer_test for readers in hotel monitoring page
            socketio.emit('reader_data', hotelchoices.name + ", " + str(hotelbookings))


        return(hotelchoices, hotelbookings)


def hotelCommit(booking, length_booked):
    with app.app_context():
        hotelname = Hotel.query.filter_by(name=booking).first()
        hotelname.length_booked = length_booked
        db.session.commit()


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count})




#semaphore version of reader, not currently planned to be used
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

#reader function with writer priority
def readers(hotel=""):
   global activeWriter, waitingWriter, activeReader, waitingReader
   time.sleep(random.randint(1, 4))
   with lock:
       while (activeWriter + waitingWriter) > 0:
           waitingReader += 1
           conditionread.wait()
           waitingReader -= 1
       activeReader += 1
   hotelchoices, hotelbookings = hotelquery(hotel)
   time.sleep(random.randint(2,3))
   with lock:
       activeReader -= 1
       if activeReader == 0 and waitingWriter > 0:
           conditionwrite.notify()

   return (hotelchoices, hotelbookings)


#writer function for writer priority
def writers(booking, length_booked):
    global activeWriter, waitingWriter, activeReader, waitingReader
    time.sleep(random.randint(1, 4))
    with lock:
        while (activeWriter + activeReader) > 0:
            waitingWriter += 1
            socketio.emit('reader_data', "waiting writer action")
            conditionwrite.wait()
            waitingWriter -= 1
        activeWriter += 1
    hotelCommit(booking, length_booked)
    writerMessage = "Writer Action: " + booking + ", " + str(length_booked)
    socketio.emit('reader_data', writerMessage)
    time.sleep(random.randint(2, 4))
    with lock:
        activeWriter -= 1
        if waitingWriter > 0:

            conditionwrite.notify()
        else:
            conditionread.notify_all()

# log event
@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

# generates 10 random readers and 5 random writers
@socketio.event
def reader_writer_test():
    with ThreadPoolExecutor() as executor:
        future = executor.submit(readers)
        hotelchoices, hotelbookings = future.result()

    hotelNum = len(hotelchoices)
    randomNums = []

    with ThreadPoolExecutor() as executor:
        for _ in range(10):
            randomHotel2 = random.choice(hotelchoices)
            executor.submit(readers, randomHotel2)


        for i in range(hotelNum):
            randomNum = random.randint(10, 30)
            randomNums.append(randomNum)
            executor.submit(writers, hotelchoices[i], randomNum)
            executor.submit(maintain_booking, hotelchoices[i], randomNums[i])


@socketio.event
def connect():
    '''
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    '''
    emit('my_response', {'data': 'Connected', 'count': 0})


# event for reading and printing database values
#source for threadpoolexecutor https://docs.python.org/3/library/concurrent.futures.html
@socketio.event
def reader_ping():
    ### CRITICAL SECTION (b/c calls hotelquery) -->
    #thread pool executor uses limited number of threads to get hotelquery. submit calls the reader function and future stores the query result from ready
    with ThreadPoolExecutor() as executor:
         future = executor.submit(readers)
         hotelchoices, hotelbookings = future.result()
    ### CRITICAL SECTION <--
    data = dict(zip(hotelchoices,hotelbookings))
    data = json.dumps(data)
    JS_data = json.loads(data)
    emit('reader_data', JS_data)


# counts down length booked and resets the booking value to 0 when this is done, 
# so booking can be made by additional writers
# NOTE: still need to get this to work

def maintain_booking(booking, length_booked):
    time.sleep(int(length_booked))
    with app.app_context():
    ### CRITICAL SECTION -->
        writers(booking, 0)
    ### CRITICAL SECTION <--
        print("finished thread\n",file=sys.stderr)
  

# security users and roles
class Role(db.Model, fsqla.FsRoleMixin):
    pass

class User(db.Model, fsqla.FsUserMixin):
    pass



# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Views

# index page
@app.route("/")
def index():
    return render_template('index.html')

# booking monitor page
@app.route("/reader")
def reader():
    return render_template('reader.html')

# booking creation page (username password required)
#username: test@me.com
#password: password
@app.route('/create', methods=('GET', 'POST'))
@auth_required()
def create():
    
    #get only hotel options
    ### CRITICAL SECTION (b/c calls hotelquery) -->
    with ThreadPoolExecutor() as executor:
        future = executor.submit(readers)
        hotelchoices = future.result()[0]
    ### CRITICAL SECTION <--
    
    if request.method == 'POST':
        
        #### get to work with auth-required, also get to work as a query of database
        result = request.form
        if not result:
            flash('Hotel Name is required!')
        else:
            booking = result.get("hotelname")
            length_booked = result.get("hnumber")

            if booking in hotelchoices: 
                ### CRITICAL SECTION -->
                with ThreadPoolExecutor() as executor:
                    executor.submit(writers, booking, length_booked)
                ### CRITICAL SECTION <--

                # now we wait for the length of the booking, then make hotel available again
                # using a separate thread for this so that the webpage will return result.html and not just wait for the booking to complete
                t = threading.Thread(target=maintain_booking, args=(booking, length_booked))
                #would like to make another thread (t2?) that runs maintain_booking
                #t2 = threading.Thread(target=maintain_booking(booking, length_booked))
                t.start()
                #t2.start()

            else: 
                flash('Hotel not in system')

            return render_template("result.html", result=result)
        
    
    return render_template('create.html', hotelchoices = hotelchoices)
  


# one time setup
with app.app_context():
    ### CRITICAL SECTION -->
    # Create User to test with
    db.create_all()
    if not security.datastore.find_user(email="test@me.com"):
        security.datastore.create_user(email="test@me.com", password=hash_password("password"))
    db.session.commit()

    db.session.add(Hotel('Marriott', 0))
    db.session.add(Hotel('Hyatt',0))
    db.session.commit()

    hotels = Hotel.query.all()
    ### CRITICAL SECTION <--
    print(hotels)

if __name__ == '__main__':
    socketio.run(app, port=8080)
