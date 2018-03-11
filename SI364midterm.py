###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
# Import statements
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
# ## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)

######################################
######## HELPER FXNS (If any) ########
######################################
def get_or_create_comment(comment_string, search):
    comment = db.session.query(Comment).filter_by(comment=comment_string).first()
    if not comment:
        comment = Comment(comment=comment_string, search_id=search.id)
        db.session.add(comment)
        db.session.commit()
    return comment

def get_or_create_search(username, param, search_string, comment):
    search = db.session.query(Search).filter_by(username=username, search_param=param, search=search_string).first()
    if not search:
        search = Search(username=username, search_param=param, search=search_string)
        db.session.add(search)
        db.session.commit()
    return search

def get_or_create_player(player_name, result):
    player = db.session.query(Player).filter_by(player=player_name).first()
    if not player:
        player = Comment(player=player_name, result=result.id)
        db.session.add(player)
        db.session.commit()
    return player

def get_or_create_result(result_url):
    result = db.session.query(Result).filter_by(result_url = result_url).first()
    if not result:
        result = Result(result_url=result_url)
        db.session.add(result)
        db.session.commit()
    return result

def add_to_dictionary(dictionary, key, value):
    if value:
        dictionary[key] = value

##################
##### MODELS #####
##################

class Comment(db.Model):
    __tablename__ = "Comment"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(500))
    search_id = db.Column(db.Integer, db.ForeignKey('Search.id'))

    def __repr__(self):
        return "Comment: {} ({})".format(self.comment, self.user_id)

class Search(db.Model):
    __tablename__ = 'Search'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True)
    search_param = db.Column(db.String(16))
    search = db.Column(db.String(64))
    comment = db.relationship("Comment", backref=db.backref('Search', lazy=True))

    def __repr__(self):
        return "Search: {} ({})".format(self.search, self.username)

class Player(db.Model):
    __tablename__ = 'Player'
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(64))
    result_id = db.Column(db.Integer, db.ForeignKey('Result.id'))


class Result(db.Model):
    __tablename__ = 'Result'
    id = db.Column(db.Integer, primary_key=True)
    result_url = db.Column(db.String(200))
    player = db.relationship("Player", backref=db.backref('Result', lazy=True))


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
            raise ValidationError("Search parameter invalid. Try again.")


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
    if form.errors:
        flash(form.errors)
    if request.method == 'POST' and form.validate_on_submit():
        result = {}
        search_db = get_or_create_search(name, param, search, comment)
        get_or_create_comment(comment, search_db)
        if param == 'player':
            result = get_or_create_result('http://nflArrest.com/api/v1/crime/topPlayers/' + search)
            get_or_create_player(search, result)
        flash('Form submitted')
        if param == 'crime':
            add_to_dictionary(result, 'player', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topPlayers/' + search).text))
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topTeams/' + search).text))
            add_to_dictionary(result, 'position', json.loads(requests.get('http://nflArrest.com/api/v1/crime/topPositions/' + search).text))
        elif param == 'player':
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/player/topTeams/' + search).text))
            add_to_dictionary(result, 'position', json.loads(requests.get('http://nflArrest.com/api/v1/player/topPositions/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/player/topCrimes/' + search).text))
        elif param == 'team':
            add_to_dictionary(result, 'player', json.loads(requests.get('http://nflArrest.com/api/v1/team/topPlayers/' + search).text))
            add_to_dictionary(result, 'position', json.loads(requests.get('http://nflArrest.com/api/v1/team/topPositions/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/team/topCrimes/' + search).text))
        else:
            # position
            add_to_dictionary(result, 'team', json.loads(requests.get('http://nflArrest.com/api/v1/position/topTeams/' + search).text))
            add_to_dictionary(result, 'crime', json.loads(requests.get('http://nflArrest.com/api/v1/position/topCrimes/' + search).text))
        if not result:
            flash('Search invalid. Try again.')
            return redirect(url_for('home'))
        return render_template('result.html', result=result)
    else:
        flash('Search invalid. Try again.')
        return redirect(url_for('home'))


# view database stuff
@app.route('/all_comments')
def all_comments():
    comments = Comment.query.all()
    all_comments = []
    for comment in comments:
        search = Search.query.filter_by(id=comment.search_id).first()
        all_comments.append((comment.comment, search.username, search.search_param, search.search))
    return render_template('all_comments.html', all_comments=all_comments)

# references
@app.route('/crimesList')
def all_crimes():
    crimes = json.loads(requests.get('http://nflarrest.com/api/v1/crime').text)
    return render_template('crimes.html', crimes=crimes)

@app.route('/playerList')
def all_players():
    players = json.loads(requests.get('http://nflarrest.com/api/v1/player').text)
    print(players)
    return render_template('players.html', players=players)

@app.route('/teamList')
def all_teams():
    teams = json.loads(requests.get('http://nflarrest.com/api/v1/team').text)
    return render_template('teams.html', teams=teams)

@app.route('/positionList')
def all_positions():
    positions = json.loads(requests.get('http://nflarrest.com/api/v1/position').text)
    return render_template('positions.html', positions=positions)

# errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404




## Code to run the application...

# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!
if __name__ == '__main__':
    db.create_all()
    app.run(use_reloader=True, debug=True)
