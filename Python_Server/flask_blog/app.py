import os

from flask import Flask, render_template_string, request, flash, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, auth_required, hash_password
from flask_security.models import fsqla_v3 as fsqla
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import create_engine, ForeignKey, String, update, bindparam, MetaData, insert
from typing import List
from typing import Optional


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

# Create database connection object
db = SQLAlchemy(app)

# Define models
fsqla.FsModels.set_db_info(db)

#### begin new section

#create engine
engine = db.create_engine("sqlite://", echo=True)
meta = db.MetaData()

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

def init_db(): 
    db.create_all()

    db.session.add(Hotel('Marriott', 0))
    db.session.add(Hotel('Hyatt',0))
    db.session.commit()

    hotels = Hotel.query.all()
    print(hotels)






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

@app.route('/create', methods=('GET', 'POST'))
#@auth_required()
def create():
    
    if request.method == 'POST':
        #return redirect(url_for('index'))
        #booking = request.form.get("hname")
        #time = request.form.get("hnumber")
        result = request.form
        #return redirect(url_for('index')
        if not result:
            flash('Hotel Name is required!')
        else:
            booking = result.get("hname")
            length_booked = result.get("hnumber")
            db.session.add(Hotel(booking,length_booked))
            db.session.commit()
            return render_template("result.html", result=result)
        
    
    return render_template('create.html')
  

# one time setup
with app.app_context():
    # Create User to test with
    db.create_all()
    if not security.datastore.find_user(email="test@me.com"):
        security.datastore.create_user(email="test@me.com", password=hash_password("password"))
    db.session.commit()

if __name__ == '__main__':
    init_db()

    #create_data()
    app.run()