#Import Flask Library

from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import hashlib
import time
import datetime
import os 
import secrets 
from PIL import Image 


IMAGES_DIR = os.path.join(os.getcwd(), "photos")

SALT = 'cs3083'

#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='Finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person(username, password) VALUES(%s, %s)'
        cursor.execute(ins, (username, password))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home', methods=['GET'])
def home():
    if 'username' in session: #only return template of home if logged in (use in post)
        return render_template('home.html')
    else: 
        return render_template('index.html')

# helper fxn for post
# def savePicture(filename):

#     random_hex = secrets.token_hex(8)
#     _, f_ext = os.path.splitext(filename)
#     picture_fn = random_hex + f_ext
#     picture_path = os.path.join(app.root_path, 'photos', filename)
#     output_size = (400, 500)
#     i = Image.open(picture_path)
#     i.thumbnail(output_size)
#     i.save(picture_path)

#     return picture_fn

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' in session:
        if request.method == 'POST':

            image_file = request.files.get("photo", "")
            image_name = image_file.filename
            filepath = os.path.join(IMAGES_DIR, image_name)
            image_file.save(filepath)

            #picture = savePicture(fileDirectory)
            if request.form.get("allFollowers"): # form is a dict [] ,get is a fxn ()
                allFollowers = request.form.get("allFollowers")
            else:
                 allFollowers = ""

            caption = request.form['caption']
            ts = time.time()
            timestamp=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.cursor()
            ins = 'INSERT INTO Photo(postingDate, filePath, allFollowers, caption, poster)\
                    VALUES(%s, %s, %s, %s, %s)'
            if allFollowers:
                cursor.execute(ins, (timestamp, filepath, 1, caption, session['username']))
                conn.commit()
            else:
                cursor.execute(ins, (timestamp, filepath, 0, caption, session['username']))
                conn.commit() 
            cursor.close()
        return render_template('post.html')
    else: 
        return render_template('index.html')
 
@app.route('/sendrequests', methods=['GET', 'POST'])
def sendRequests():
    if request.form: #submitted   
        username = request.form['username']
        cursor = conn.cursor()
        query = "SELECT * FROM Person WHERE username = %s" 
        cursor.execute(query,(username))
        data=cursor.fetchone() #expecting one username 
        if data: # is a matching username
            query = "SELECT followStatus FROM Follow WHERE follower = %s and followee = %s"
            cursor.execute(query,(session["username"], username))
            fStatus = cursor.fetchone()
            print(fStatus)
            if (fStatus):
                if (fStatus["followStatus"]==1): # does exist and accepted requets, followStatus==1  
                    message = "%s already accepted your follow request. " % username 
                elif (fStatus["followStatus"]==0):  # does exist, havent accepted request yet ,  followStatus==0
                    message = "You have already sent a request to %s" % username 
            else:   # didnt send request yet 
                ins = "INSERT INTO Follow(follower, followee, followStatus) VALUES (%s, %s, %s)"
                cursor.execute(ins, (session["username"], username, 0)) #set followstatus to 0
                conn.commit()
                message = "Request sent!"
            query = 'SELECT * FROM Follow WHERE followee = %s AND follower = %s'
            cursor.execute(query,(username, session['username']))
            data = cursor.fetchone()
            if(data['followStatus'] == 1):
                error  = f'You already follow {username}!'
                cursor.close()
                return render_template('sendrequests.html', message = error)
            elif (data['followStatus'] == 0):
                error = f'You already sent a request to {username}'
                cursor.close()
                return render_template('sendrequests.html', message = error)
            else: #WHY IS THIS CASE NOT WORKING???? showing "already sent"
                print(data)
                message = f'Request successfully sent to {username}'
                return render_template('sendrequests.html', message = message)
                query = 'INSERT INTO Follow VALUES(%s,%s,0)'
                cursor.execute(query,(username, session['username']))
                conn.commit()
                cursor.close()
        else: # no matching username 
            error = 'That username does not exist, try another one'
            cursor.close()
            return render_template('sendrequests.html', message = error)
            cursor.close()

    return render_template('sendrequests.html') #

@app.route('/managerequests', methods=['GET', 'POST'])
def manageRequests():
    cursor= conn.cursor()
    query= "SELECT follower FROM Follow WHERE followee =%s AND followStatus = 0"
    cursor.execute(query, (session['username']))
    data= cursor.fetchall()
    if request.form:
        selectedUsers = request.form.getlist('selectedUsers')
        for user in selectedUsers:
            if request.form['action'] ==  'Accept':
                query = 'UPDATE Follow SET followStatus = 1 WHERE followee=%s AND follower = %s'
                cursor.execute(query, (user,session['username']))
                conn.commit()
                flash('The selected friend requests have been accepted!')
            elif request.form['action'] == 'Decline':
                query = 'DELETE FROM Follow WHERE followee = %s AND follower = %s'
                cursor.execute(query, (user, session['username']))
                conn.commit()
                flash('The selected friend requests have been deleted')
        return redirect(url_for('manageRequests'))
        # handle form goes here
    cursor.close()
    return render_template('managerequests.html', followers = data)






    
@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
