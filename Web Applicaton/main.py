from __future__ import division
import numpy as np
import pandas as pd
# import time
# import re
# import os
from collections import Counter
import altair as alt

### Flask imports
import requests
from flask import Flask, render_template, session, request, redirect, flash, Response, url_for
from flask_sqlalchemy import SQLAlchemy
# from flask_login import current_user
### Video imports ###
from library.video_emotion_recognition import *

from nltk import *
from tika import parser
from werkzeug.utils import secure_filename
import tempfile

# Flask config
app = Flask(__name__)
app.secret_key = b'(\xee\x00\xd4\xce"\xcf\xe8@\r\xde\xfc\xbdJ\x08W'
app.config['UPLOAD_FOLDER'] = '/Upload'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/emotion_monitor'
db = SQLAlchemy(app)


################################################################################
################################## INDEX #######################################
################################################################################
class Hosts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    name = db.Column(db.String(120), unique=False, nullable=False)


class Audience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    name = db.Column(db.String(120), unique=False, nullable=False)


# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/registration', methods=("POST", "GET"))
def registration():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        hosts = Hosts.query.order_by(Hosts.name).all()
        if role == "host":
            entry = Hosts(email=email, password=password, name=name)
            flash(name + ' you successfully join as a Host')
            db.session.add(entry)
            db.session.commit()
            return render_template('login2.html',hosts=hosts)
        elif role == "audience":
            entry = Audience(email=email, password=password, name=name)
            flash(name + ' you successfully join as a Audience')
            db.session.add(entry)
            db.session.commit()
            return render_template('login2.html',hosts=hosts)
        else:
            flash('Please fill up the form correctly')
    return render_template('registration2.html')


@app.route('/logout', methods=("POST", "GET"))
def logout():
    session.clear()
    return render_template('index.html')
@app.route('/team', methods=("POST", "GET"))
def team():
    return render_template('team.html')

@app.route('/login', methods=("POST", "GET"))
def login():
    hosts = Hosts.query.order_by(Hosts.name).all()
    session.clear()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if role == "host":

            user = Hosts.query.filter_by(email=email).first()

            flash(user.name + ' you successfully logged in as a Host')
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['role'] = 'host'
            session['loggedIn'] = True
            return redirect(url_for('index'))

        elif role == "audience":

            user = Audience.query.filter_by(email=email).first()

            flash(user.name + ' you successfully logged in as a Host')
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['role'] = 'audience'
            session['loggedIn'] = True
            return redirect(url_for('index'))
        else:
            flash('Please inter your credential correctly')
    print(hosts)
    return render_template('login2.html', hosts=hosts)


################################################################################
################################## RULES #######################################
################################################################################

# Rules of the game
@app.route('/rules')
def rules():
    return render_template('rules.html')


################################################################################
############################### VIDEO INTERVIEW ################################
################################################################################

# Read the overall dataframe before the user starts to add his own data
df = pd.read_csv('static/js/db/histo.txt', sep=",")


# Video interview template
@app.route('/video', methods=['POST', "GET"])
def video():
    return render_template('video.html')


# Display the video flow (face, landmarks, emotion)
@app.route('/video_1', methods=['POST'])
def video_1():
    try:
        scheduler_time = request.form.get('time')
        # Response is used to display a flow of information
        return Response(gen(scheduler_time), mimetype='multipart/x-mixed-replace; boundary=frame')
    # return Response(stream_template('video.html', gen()))
    except:
        return None


# Dashboard
@app.route('/video_dash', methods=("POST", "GET"))
def video_dash():
    try:
        if session['role'] != 'host':
            return render_template('index.html')
    except:
        return render_template('index.html')
    # Load personal history
    df_2 = pd.read_csv('static/js/db/histo_perso.txt')

    def emo_prop(df_2):
        return [int(100 * len(df_2[df_2.density == 0]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 1]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 2]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 3]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 4]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 5]) / len(df_2)),
                int(100 * len(df_2[df_2.density == 6]) / len(df_2))]

    emotions = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]
    emo_perso = {}
    emo_glob = {}

    for i in range(len(emotions)):
        emo_perso[emotions[i]] = len(df_2[df_2.density == i])
        emo_glob[emotions[i]] = len(df[df.density == i])

    df_perso = pd.DataFrame.from_dict(emo_perso, orient='index')
    df_perso = df_perso.reset_index()
    df_perso.columns = ['EMOTION', 'VALUE']
    df_perso.to_csv('static/js/db/hist_vid_perso.txt', sep=",", index=False)

    df_glob = pd.DataFrame.from_dict(emo_glob, orient='index')
    df_glob = df_glob.reset_index()
    df_glob.columns = ['EMOTION', 'VALUE']
    df_glob.to_csv('static/js/db/hist_vid_glob.txt', sep=",", index=False)

    emotion = df_2.density.mode()[0]
    emotion_other = df.density.mode()[0]

    def emotion_label(emotion):
        if emotion == 0:
            return "Angry"
        elif emotion == 1:
            return "Disgust"
        elif emotion == 2:
            return "Fear"
        elif emotion == 3:
            return "Happy"
        elif emotion == 4:
            return "Sad"
        elif emotion == 5:
            return "Surprise"
        else:
            return "Neutral"

    ### Altair Plot
    df_altair = pd.read_csv('static/js/db/prob.csv', header=None, index_col=None).reset_index()
    df_altair.columns = ['Time', 'Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

    angry = alt.Chart(df_altair).mark_line(color='orange', strokeWidth=2).encode(
        x='Time:Q',
        y='Angry:Q',
        tooltip=["Angry"]
    )

    disgust = alt.Chart(df_altair).mark_line(color='red', strokeWidth=2).encode(
        x='Time:Q',
        y='Disgust:Q',
        tooltip=["Disgust"])

    fear = alt.Chart(df_altair).mark_line(color='green', strokeWidth=2).encode(
        x='Time:Q',
        y='Fear:Q',
        tooltip=["Fear"])

    happy = alt.Chart(df_altair).mark_line(color='blue', strokeWidth=2).encode(
        x='Time:Q',
        y='Happy:Q',
        tooltip=["Happy"])

    sad = alt.Chart(df_altair).mark_line(color='black', strokeWidth=2).encode(
        x='Time:Q',
        y='Sad:Q',
        tooltip=["Sad"])

    surprise = alt.Chart(df_altair).mark_line(color='pink', strokeWidth=2).encode(
        x='Time:Q',
        y='Surprise:Q',
        tooltip=["Surprise"])

    neutral = alt.Chart(df_altair).mark_line(color='brown', strokeWidth=2).encode(
        x='Time:Q',
        y='Neutral:Q',
        tooltip=["Neutral"])

    chart = (angry + disgust + fear + happy + sad + surprise + neutral).properties(
        width=1000, height=400, title='Probability of each emotion over time')

    chart.save('static/CSS/chart.html')

    return render_template('video_dash.html', emo=emotion_label(emotion), emo_other=emotion_label(emotion_other),
                           prob=emo_prop(df_2), prob_other=emo_prop(df))


################################################################################
if __name__ == '__main__':
    app.run(debug=True)
