import json, sqlite3, click, functools, os, hashlib,time, random, sys
from flask import Flask, current_app, g, session, redirect, render_template, url_for, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

### DATABASE FUNCTIONS ###

def connect_db():
    return sqlite3.connect(app.database)

def init_db():
    """Initializes the database with our great SQL schema"""
    conn = connect_db()
    db = conn.cursor()
    db.executescript("""

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS notes;

CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assocUser INTEGER NOT NULL,
    dateWritten DATETIME NOT NULL,
    note TEXT NOT NULL,
    publicID INTEGER NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);

""")



### APPLICATION SETUP ###
app = Flask(__name__)
app.database = "db.sqlite3"
app.secret_key = os.urandom(32)

### SETUP RATE LIMIT OF ROUTES ###
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="memory://"
)

@app.errorhandler(429)
def ratelimit_handler(e):
    return f"""<html>
                <body>
                    <h1>429</h1>
                    <h2>Too many requests</h2>
                    <p>{e}</p>
                </body>
                </html>
            """

### ADMINISTRATOR'S PANEL ###
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route("/")
def index():
    if not session.get('logged_in'):
        return render_template('index.html')
    else:
        return redirect(url_for('notes'))


@app.route("/notes/", methods=('GET', 'POST'))
@login_required
def notes():
    importerror=""

    #Posting a new note:
    if request.method == 'POST':
        if request.form['submit_button'] == 'add note':
            note = request.form['noteinput']
            db = connect_db()
            c = db.cursor()
            statement = """INSERT INTO notes(id,assocUser,dateWritten,note,publicID) VALUES(?, ?, ?, ?, ?);"""
            print(statement)
            c.execute(statement, (None, session['userid'], time.strftime('%Y-%m-%d %H:%M:%S'), note, random.randrange(1000000000, 1000005000)))
            db.commit()
            db.close()
        elif request.form['submit_button'] == 'import note':
            noteid = request.form['noteid']
            db = connect_db()
            c = db.cursor()
            statement = """SELECT * from NOTES where publicID = ?"""
            c.execute(statement, (noteid,))
            result = c.fetchall()
            if(len(result)>0):
                row = result[0]
                statement = """INSERT INTO notes(id,assocUser,dateWritten,note,publicID) VALUES(?, ?, ?, ?, ?);"""
                c.execute(statement, (None, session['userid'], row[2], row[3], row[4]))
            else:
                importerror="No such note with that ID!"
            db.commit()
            db.close()
    
    db = connect_db()
    c = db.cursor()
    statement = "SELECT * FROM notes WHERE assocUser = ?;"
    print(statement)
    c.execute(statement, (session['userid'],))
    notes = c.fetchall()
    print(notes)
    
    return render_template('notes.html',notes=notes,importerror=importerror)


@app.route("/login/", methods=('GET', 'POST'))
@limiter.limit("10/minute")
def login():
    if not session.get('attempt'):
        session['attempt'] = 4
    
    error = ""
    if request.method == 'POST':
        loginAttempt = session['attempt']
        render_template('login.html', error = error)

        if loginAttempt == 1:
            error = "Login attempts exceeded!"
        else:
            username = request.form['username']
            password = request.form['password']

            db = connect_db()
            c = db.cursor()
            statement = "SELECT * FROM users WHERE username = ? AND password = ?"
            c.execute(statement, (username, password))
            result = c.fetchall()
            
            if len(result) > 0:
                session.clear()
                session['logged_in'] = True
                session['userid'] = result[0][0]
                session['username']= result[0][1]
                loginAttempt = 4
                session['attempt'] = loginAttempt
                return redirect(url_for('index'))
            else:
                loginAttempt -= 1
                session['attempt'] = loginAttempt
                error = f"Wrong username or password! Tries left: {loginAttempt}"
    return render_template('login.html', error=error)


@app.route("/register/", methods=('GET', 'POST'))
@limiter.limit("10/minute")
def register():
    errored = False
    usererror = ""
    passworderror = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = connect_db()
        c = db.cursor()
        pass_statement = "SELECT * FROM users WHERE password = ?"
        user_statement = "SELECT * FROM users WHERE username = ?"
        c.execute(pass_statement, (password,))

        c.execute(user_statement, (username,))
        if(len(c.fetchall())>0):
            errored = True
            usererror = "That username is already in use by someone else!"

        if(not errored):
            statement = """INSERT INTO users(id,username,password) VALUES(?, ?, ?);"""
            print(statement)
            c.execute(statement, (None, username, password))
            db.commit()
            db.close()
            return f"""<html>
                        <head>
                            <meta http-equiv="refresh" content="2;url=/" />
                        </head>
                        <body>
                            <h1>SUCCESS!!! Redirecting in 2 seconds...</h1>
                        </body>
                        </html>
                        """
        
        db.commit()
        db.close()
    return render_template('register.html',usererror=usererror,passworderror=passworderror)


@app.route("/logout/")
@login_required
def logout():
    """Logout: clears the session"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    #create database if it doesn't exist yet
    if not os.path.exists(app.database):
        init_db()
    runport = 5000
    if(len(sys.argv)==2):
        runport = sys.argv[1]
    try:
        app.run(host='0.0.0.0', port=runport) # runs on machine ip address to make it visible on netowrk
    except:
        print("Something went wrong. the usage of the server is either")
        print("'python3 app.py' (to start on port 5000)")
        print("or")
        print("'sudo python3 app.py 80' (to run on any other port)")