###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError
from wtforms.validators import Required, Length
from flask_sqlalchemy import SQLAlchemy
import requests
import json

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
app.config['SECRET_KEY'] = 'random string'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://yuxuan:root@localhost:5432/yuxuanc364midterm"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)

######################################
######## HELPER FXNS (If any) ########
######################################

def get_or_create_search(search_param, search_text):
    search = db.session.query(Search).filter_by(search_param=search_param, search_text=search_text).first()
    if not search:
        search = Search(search_param=search_param, search_text=search_text)
        db.session.add(search)
        db.session.commit()
    return search

def get_or_create_comment(comment_string, search):
    comment = db.session.query(Comment).filter_by(comment=comment_string).first()
    if not comment:
        comment = Comment(comment=comment_string, search_id=search.id)
        db.session.add(comment)
        db.session.commit()
    return comment

def get_or_create_user(username, search):
    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        user = User(username=username, search_id=search.id)
        db.session.add(user)
        db.session.commit()
    return user

def get_or_create_result(result_string, search):
    result = db.session.query(Result).filter_by(result=result_string).first()
    if not result:
        result = Result(result=result_string, search_id=search.id)
        db.session.add(result)
        db.session.commit()
    return result

def add_to_dictionary(dictionary, key, value):
    # adds value to dictionary if the value is not empty
    if value:
        dictionary[key] = value

##################
##### MODELS #####
##################

class Comment(db.Model):
    # stores comments
    __tablename__ = "Comment"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(500))
    search_id = db.Column(db.Integer, db.ForeignKey('Search.id'))

class Search(db.Model):
    # stores searches
    __tablename__ = 'Search'
    id = db.Column(db.Integer, primary_key=True)
    search_param = db.Column(db.String(16))
    search_text = db.Column(db.String(64))
    comment = db.relationship("Comment", backref=db.backref('Search', lazy=True))
    user = db.relationship("User", backref=db.backref('Search', lazy=True))
    result = db.relationship("Result", backref=db.backref('Search', lazy=True))


class User(db.Model):
    # stores user info
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    search_id = db.Column(db.Integer, db.ForeignKey('Search.id'))


class Result(db.Model):
    # stores results
    __tablename__ = 'Result'
    id = db.Column(db.Integer, primary_key=True)
    # not sure how large the result might be
    result = db.Column(db.String(40000))
    search_id = db.Column(db.Integer, db.ForeignKey('Search.id'))


###################
###### FORMS ######
###################

class SearchForm(FlaskForm):
    name = StringField("Username (between 3 and 30 characters)", validators=[Required(), Length(3, 30)])
    param = StringField("Search by (crime, player, team, position):", validators=[Required()])
    search = StringField("Enter search term", validators=[Required()])
    comment = StringField("Enter comment", validators=[Required(), Length(0, 500)])
    submit = SubmitField()

    def validate_param(self, field):
        if str(field.data) not in ['crime', 'player', 'team', 'position']:
            raise ValidationError("Search parameter invalid. Make sure it is crime, player, team, or position (case sensitive)")


#######################
###### VIEW FXNS ######
#######################

@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    return render_template('index.html', form=form)

@app.route('/result', methods=['GET', 'POST'])
def result():
    form = SearchForm()
    name = form.name.data
    param = form.param.data
    search = form.search.data
    comment = form.comment.data
    if request.method == 'POST' and form.validate_on_submit():
        result = {}
        flash('Form submitted')
        # get some relevant results and store it in a result dictionary
        if param == 'crime':
            add_to_dictionary(result, 'player', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topPlayers/' + search).text))
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topTeams/' + search).text))
            add_to_dictionary(result, 'position', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topPositions/' + search).text))
        elif param == 'player':
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/player/topTeams/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/player/topCrimes/' + search).text))
        elif param == 'team':
            add_to_dictionary(result, 'player', json.loads(requests.get('http://nflArrest.com/api/v1/team/topPlayers/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/team/topCrimes/' + search).text))
        else:
            # position
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/position/topTeams/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/position/topCrimes/' + search).text))
        
        # add info to database
        search_db = get_or_create_search(param, search)
        get_or_create_result(str(result), search_db)
        get_or_create_comment(comment, search_db)
        get_or_create_user(name, search_db)
        # make sure search is valid
        if not result:
            flash('Search invalid. Try again.')
            return redirect(url_for('home'))
        # display result
        return render_template('result.html', result=result)
    if form.errors:
        flash(form.errors)
    else:
        flash('Search invalid. Try again.')
    return redirect(url_for('home'))


# view database stuff
@app.route('/all_comments')
def all_comments():
    # displays all comments and searches in the database
    comments = Comment.query.all()
    all_comments = []
    for comment in comments:
        search = Search.query.filter_by(id=comment.search_id).first()
        user = User.query.filter_by(search_id=comment.search_id).first()
        all_comments.append((comment.comment, user.username, search.search_param, search.search_text))
    return render_template('all_comments.html', all_comments=all_comments)

# references
@app.route('/crimesList')
def all_crimes():
    # list of crimes
    crimes = json.loads(requests.get('http://nflarrest.com/api/v1/crime').text)
    return render_template('crimes.html', crimes=crimes)

@app.route('/playerList')
def all_players():
    # list of players
    players = json.loads(requests.get('http://nflarrest.com/api/v1/player').text)
    print(players)
    return render_template('players.html', players=players)

@app.route('/teamList')
def all_teams():
    # list of teams
    teams = json.loads(requests.get('http://nflarrest.com/api/v1/team').text)
    return render_template('teams.html', teams=teams)

@app.route('/positionList')
def all_positions():
    # list of positions
    positions = json.loads(requests.get('http://nflarrest.com/api/v1/position').text)
    return render_template('positions.html', positions=positions)

# errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404




## Code to run the application...
if __name__ == '__main__':
    db.create_all()
    app.run(use_reloader=True, debug=True)
