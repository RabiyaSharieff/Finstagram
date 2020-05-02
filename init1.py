#Import Flask Library

from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import hashlib
import time
import datetime
import os 
import secrets 
from PIL import Image 


IMAGES_DIR = os.path.join(os.getcwd(), "images")

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

def encrypt(strToHash):
    encoded = hashlib.sha256(str.encode(strToHash))
    return encoded.hexdigest()


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
    passwordHashed = encrypt(password + SALT)

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, passwordHashed))
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
    #password = request.form['password']
    passwordHashed = encrypt(request.form['password'] + SALT) #encypts and store in database 
    firstName = request.form['fname']
    lastName = request.form['lname']
    email = request.form['emailAddy']

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
        ins = 'INSERT INTO Person(username, password, firstName, lastName, email) VALUES(%s, %s,  %s, %s, %s)'
        cursor.execute(ins, (username, passwordHashed, firstName, lastName, email))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home', methods=['GET'])
def home():
    # View visible photos 
    username = session['username'] # get user info 
    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE username =  %s'
    cursor.execute( query, (username))
    data = cursor.fetchone()
    firstName = data['firstName']
    lastName = data['lastName']
    # get the photos visible to the username
    query = 'SELECT pID,postingDate, filePath, allFollowers, caption, poster FROM Photo WHERE poster = %s OR pID IN (SELECT pID FROM Photo WHERE poster != %s AND allFollowers = 1 AND poster IN (SELECT followee FROM Follow WHERE follower = %s AND followee = poster AND followStatus = 1)) OR pID IN (SELECT pID FROM SharedWith NATURAL JOIN BelongTo NATURAL JOIN Photo WHERE username = %s AND poster != %s) ORDER BY postingDate DESC'
    cursor.execute(query, (username, username, username, username, username))
    data = cursor.fetchall()

    for post in data: # post is a dictionary within a list of dictionaries for all the photos
        #tags
        query = 'SELECT username, firstName, lastName FROM Tag NATURAL JOIN Person NATURAL JOIN Photo WHERE tagStatus = 1 AND pID = %s'
        cursor.execute(query, (post['pID']))
        resultOne = cursor.fetchall()

        if (resultOne):
            post['tagees'] = resultOne
            # print(post)

        #reacts
        query = 'SELECT firstName, lastName FROM Person WHERE username = %s'
        cursor.execute(query, (post['poster']))
        ownerData = cursor.fetchone()
        post['firstName'] = ownerData['firstName']
        post['lastName'] = ownerData['lastName']
        query = "SELECT username, comment, emoji FROM ReactTo WHERE pID = %s"
        cursor.execute(query, (post['pID']))
        resultTwo = cursor.fetchall()
        print(post['pID'])
        print("The result:" , resultTwo)

        if (resultTwo):
            print("Made it here")
            post['reacters'] = resultTwo

    cursor.close()
    return render_template('home.html', username=username, firstName=firstName, lastName =lastName, posts = data)


#check how files are saved 
@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' in session:
        cursor = conn.cursor()
        query= 'SELECT groupName FROM FriendGroup WHERE groupCreator = %s'
        cursor.execute(query, (session['username']))
        groups = cursor.fetchall() #returns a list of 
        cursor.close()

        message = ""
        if request.method == 'POST':

            image_file = request.files.get("photo", " ")
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
                message="Successfully shared with all followers!"
                conn.commit()
            else:
                cursor.execute(ins, (timestamp, filepath, 0, caption, session['username']))
                conn.commit()
                myGroups = request.form.getlist('groups')
                for group in myGroups:
                    ins= "INSERT INTO SharedWith(pID, groupName, groupCreator) VALUES(LAST_INSERT_ID(), %s, %s)"
                    cursor.execute(ins, (group, session['username']))
                    message= "Successfully shared with the groups you selected!"
                conn.commit()
            cursor.close()
        return render_template('post.html', message=message, groups=groups)
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
            if (fStatus): # check if we have previously sent a request
                if (fStatus["followStatus"]==1): # does exist and accepted requets, followStatus==1  
                    message = f'You already follow {username}!'
                elif (fStatus["followStatus"]==0):  # does exist, havent accepted request yet ,  followStatus==0
                    message = f'You have already sent a request to {username}'
            else:   # didnt send request yet, send one
                ins = "INSERT INTO Follow(follower, followee, followStatus) VALUES (%s, %s, %s)"
                cursor.execute(ins, (session["username"], username, 0)) #set followstatus to 0
                conn.commit()
                message = f'Request successfully sent to {username}'

        else: # no matching username 
            message = f'{username} does not exist, try again'
        cursor.close()
        return render_template('sendrequests.html', message = message)

    return render_template('sendrequests.html')

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
                cursor.execute(query, (session['username'], user))
                conn.commit()
                flash('The selected friend requests have been accepted!')
            elif request.form['action'] == 'Decline':
                query = 'DELETE FROM Follow WHERE followee = %s AND follower = %s'
                cursor.execute(query, (session['username'], user))
                conn.commit()
                flash('The selected friend requests have been deleted')
        return redirect(url_for('manageRequests'))
        # handle form goes here
    cursor.close()
    return render_template('managerequests.html', followers = data)


@app.route('/addFriendGroup', methods=['GET', 'POST'])
def addFriendGroup():
    if request.form:
        groupName = request.form['groupName']
        description = request.form['description']
        cursor = conn.cursor()
        # check to make sure the current user doest already created a group with groupName 
        query = 'SELECT * FROM FriendGroup WHERE groupCreator = %s AND groupName = %s'
        cursor.execute(query, (session['username'], groupName))
        data = cursor.fetchone()
        if data: # not good, return error message
            error = f'You already have a friend group called {groupName}'
            return render_template('addFriendGroup.html', message = error)
        else: # good, add group into database
            query = 'INSERT INTO FriendGroup VALUES(%s,%s,%s)'
            cursor.execute(query, (groupName, session['username'],description))
            
            # If the group is created successfully, Finstagram adds the current user as a
            # member of the group.
            query_b = 'INSERT INTO BelongTo VALUES (%s,%s,%s)'
            cursor.execute(query_b, (session['username'], groupName, session['username']))
            conn.commit()
            flash(f'Successfully created and belong to the {groupName} friend group')
            return redirect(url_for('addFriendGroup'))
    
    return render_template('addFriendGroup.html')




    
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
