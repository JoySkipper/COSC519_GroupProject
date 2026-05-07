# COSC 519 Group Project
## Reader-Writer Synchronization Using a Client-Server System 
### By Joy "Wilson" Skipper & Ian Smith

<br><br>

## Problem and Objective

<p>The core objective of the project is to demonstrate and solve the Reader-Writer problem through the implementation of a client-server system. The server simulates multiple clients accessing the same server through the utilization of processes and threads. The server allows proper regulation of requests to the server by allowing multiple readers to access the data on the server while restricting any access to the server once a writer has begun modifying the data on the server. Synchronization techniques such as the use of locks and correctness constraints prevent data conflicts from occurring due to a client reading data that is being modified by a writer and ensure consistency of the data being accessed by the readers. </p>

## Implementation

<p>We implemented these objectives through the metaphor of a webpage that books hotel rooms for a number of seconds specified by the user. This includes both webpages where the user can "book" a hotel for a specified number of seconds (writer), view the current hotel bookings (reader) and several simulated reader and writers clients working on the database in the background to simulate having several clients at once on the web server. </p>

<p>The general framework uses Python and the Web Server Gateway Interface (WSGI) web application framework known as Flask. The database setup used SQLAlchemy, an Object Relational Mapper (ORM) for using SQL databases with Python. For live views and changes to the database, Flasks own module SocketIO was used, which creats a permanent, bi-directional communication over a transmission control protocol (TCP) connection. SocketIO was a core component of this setup which allowed the use of multiple readers and writers while viewing a single webpage instance. </p>

## How to Run the Server

Clone the repo, and set up a python3 environment. Use pip to install the following tools: 

```
pip install flask
pip install flask_sqlalchemy
pip install flask_security
pip install flask_socketio
pip install argon2_cffi
```
finally, navigate to the flask_blog/ directory and run the following command: 

```
flask run --port 8080
```

## Summary of Participant Roles

<br>

### Wilson's Role: 

<p>Primarily worked on the setup of the web server. This included setting up the flask environment using SQLAlchemy to create a database to hold the hotel booking data, setting up communication with SocketIO so that live changes could be made, and setting up all webpages. She set up the booking webpage to create changes to the database and mark the hotels as booked, and the reader page which regularly queries the database for the latest data on all hotel bookings. </p>


## Ian's Role: 

<p>Primarily worked on implementation of reader and writer logic and proper usage and synchronization of readers and writers. Set up a Test Readers and Writers button to generate 10 readers and a writer for each room for demonstration of simulated logic. Add usage of readers and writers to relevant functions of the web server with readers threads generated whenever a read operation is sent to the database to retrieve room information and writer threads when a booking is made with an update operation.</p>

## References

**Flask**:

Documentation Pages: 
<br>

https://flask.palletsprojects.com/en/stable/
https://flask-user.readthedocs.io/en/latest/

Flask Guide on Setting Up Logins: 
<br>
https://community.intersystems.com/post/flask-and-flask-login-guide-building-secure-web-applications

Example of a web application using flask in Python 3: 
<br>
https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3

**SQLALchemy:**

SQLAlchemy Documentation: 
<br>
https://docs.sqlalchemy.org/en/20/

Roles in SQLAlchemy: 
<br>
https://www.osohq.com/post/sqlalchemy-role-rbac-basics

**SocketIO:** 

SocketIO documentation:
<br>
https://flask-socketio.readthedocs.io/en/latest/api.html

Explanation of using SocketIO with flask:
<br>
https://blog.miguelgrinberg.com/post/easy-websockets-with-flask-and-gevent?source=post_page-----fb55f9dad100---------------------------------------
https://github.com/miguelgrinberg/Flask-SocketIO

**SQLite:**

SQLite Commands reference: 
<br>
https://www.tutorialspoint.com/sqlite/sqlite_commands.htm


**Many how-to's from GeeksforGeeks.org:**
<br>
https://www.geeksforgeeks.org/python/convert-python-list-to-json/
https://www.geeksforgeeks.org/python/creating-instance-objects-in-python/
https://www.geeksforgeeks.org/python/sqlalchemy-core-creating-table/
https://www.geeksforgeeks.org/html/retrieving-html-from-data-using-flask/
https://www.geeksforgeeks.org/python/python-introduction-to-web-development-using-flask/
https://www.geeksforgeeks.org/python/python-flask-request-object/
https://www.geeksforgeeks.org/python/querying-and-selecting-specific-column-in-sqlalchemy/


