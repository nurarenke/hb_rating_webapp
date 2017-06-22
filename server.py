"""Movie Ratings."""

from jinja2 import StrictUndefined

from flask import Flask, jsonify, render_template, redirect, request, flash, session
from flask_debugtoolbar import DebugToolbarExtension

from model import connect_to_db, db, User, Rating, Movie

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

# Normally, if you use an undefined variable in Jinja2, it fails
# silently. This is horrible. Fix this so that, instead, it raises an
# error.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""
    # a = jsonify([1,3])
    return render_template("homepage.html")


@app.route("/users")
def user_list():
    """Show list of users."""

    users = User.query.all()
    return render_template("user_list.html", users=users)


@app.route('/users/<user_id>')
def user_info(user_id):
    """ Render user info page"""

    user = User.query.filter_by(user_id=user_id).first()
    user_ratings = user.ratings

    return render_template("user_info.html",
                            user=user, 
                            user_ratings=user_ratings)


@app.route('/rate_movie', methods=["POST"])
def rate_movie():
    """Record new movie rating or update existing"""

    movie_id = request.form.get("movie_id")
    user_id = request.form.get("user_id")
    score = request.form.get("score")

    rating = Rating(user_id=user_id,
                        movie_id=movie_id,
                        score=score)
    db.session.add(rating)
    db.session.commit()

    return redirect('/movies/{}'.format(movie_id))

@app.route('/movies')
def movie_list():
    '''Show list of movies.'''

    movies = Movie.query.order_by(Movie.title).all()
    return render_template('movies_list.html', movies=movies)

@app.route('/movies/<movie_id>')
def movie_info(movie_id):
    '''Display movie info about one particular movie'''

    movie= Movie.query.filter_by(movie_id=movie_id).first()
    movie_ratings = movie.ratings

    return render_template('movie_info.html',
                            movie=movie,
                            movie_ratings=movie_ratings)


@app.route("/register", methods=["GET"])
def register_form():
    """Displays registration form"""

    return render_template("register_form.html")


@app.route("/register", methods=["POST"])
def register_process():
    """Register user in DB """

    # since we have a POST request, lookup for arguments in request.form
    new_user_email = request.form.get('email')
    password = request.form.get('password')

    query = User.query.filter_by(email = new_user_email).first() 
    print query

    # check if user already in DB, if not - add him
    if query:
        flash("Already in DB")
    else:
        user = User(email=new_user_email,
                     password=password)
        db.session.add(user)
        db.session.commit()
        flash("New user - {} - succesfully created".format(new_user_email))

    return redirect("/")


@app.route('/login', methods=['GET'])
def login_form():
    """Displays the login form"""

    return render_template('login_form.html')


@app.route('/login_user', methods=['GET'])
def login_user():
    """ Logs user in and add his ID in the (flask) session object if it:
        - exists in database
        - and password provided matches password in the database

        Otherwise:
            catches errors, flash messages and redirect to random places
    """

    # since we have a GET request, lookup for arguments in request.args
    email = request.args.get("email")
    password = request.args.get("password")

    user = User.query.filter_by(email=email).first()

    if user:
        if user.password == password:
            flash('You were successfully logged in')
            session["current_user"] = user.user_id
            return redirect("users/{}".format(user.user_id))
        else:
            flash('Wrong credentials. Try again!')
            return redirect("/login")
    else:
        flash('Sorry, {}, you are not our user. Shame on you!'.format(email))
        return redirect("/register")


@app.route('/logout')
def logout():
    """Logout user

       remove current_user from flask.session
       flash success message
       and redirect to homepage
    """

    del session["current_user"]
    flash('You were logged out. See you later!')

    return redirect('/')


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)
    app.run(port=5000, host='0.0.0.0')
