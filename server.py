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


@app.route("/rate_movie", methods=["POST"])
def rate_movie():
    """Record new movie rating or update existing"""

    movie_id = request.form.get("movie_id")
    user_id = request.form.get("user_id")
    score = request.form.get("score")
    rating = Rating.query.filter_by(user_id=user_id, movie_id=movie_id).first()

    # update score in ratings if movie already rated by user
    if rating:
        # UPDATE table_name
        # SET column1 = value1, column2 = value2, ...
        # WHERE condition;

        # rating.update({'score': score})

        rating.score = score
        flash("Rating for movie updated for current user")
    else:
        rating = Rating(user_id=user_id, movie_id=movie_id, score=score)
        db.session.add(rating)
        flash("New rating created")

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

    movie= Movie.query.get(movie_id)

    user_id = session.get("current_user")

    if user_id:
        user_rating = Rating.query.filter_by(
            user_id=user_id, movie_id=movie_id).first()
    else:
        user_rating = None

    #Get average rating of movie

    rating_scores = [r.score for r in movie.ratings]    
    num_of_raters = len(rating_scores)
    avg_rating = float(sum(rating_scores)) / num_of_raters

    prediction = None

    # Prediction code: only predict if the user hasn't rated it.

    if (not user_rating) and user_id:
        user = User.query.get(user_id)
        if user:
            prediction = user.predict_rating(movie)

     # Either use the prediction or their real rating
    if user_rating:
        # User has already scored for real; use that
        effective_rating = user_rating.score
    elif prediction:
        # User hasn't scored; use our prediction if we made one
        effective_rating = prediction
    else:
        # User hasn't scored, and we couldn't get a prediction
        effective_rating = None

    # Get the eye's rating, either by predicting or using real rating

    the_eye = (User.query.filter_by(email="the-eye@of-judgment.com")
                         .one())

    eye_rating = Rating.query.filter_by(
        user_id=the_eye.user_id, movie_id=movie.movie_id).first()

    if eye_rating is None:
        eye_rating = the_eye.predict_rating(movie)

    else:
        eye_rating = eye_rating.score

    if eye_rating and effective_rating:
        difference = abs(eye_rating - effective_rating)
    else:
        # We couldn't get an eye rating, so we'll skip difference
        difference = None

      # Depending on how different we are from the Eye, choose a
    # message

    BERATEMENT_MESSAGES = [
        "I suppose you don't have such bad taste after all.",
        "I regret every decision that I've ever made that has " +
            "brought me to listen to your opinion.",
        "Words fail me, as your taste in movies has clearly " +
            "failed you.",
        "That movie is great. For a clown to watch. Idiot.",
        "Words cannot express the awfulness of your taste."
    ]

    if difference is not None:
        beratement = BERATEMENT_MESSAGES[int(difference)]

    else:
        beratement = None


    return render_template('movie_info.html',
                        movie=movie,
                        user_rating=user_rating,
                        average=avg_rating,
                        num_of_raters=num_of_raters,
                        prediction=prediction,
                        beratement=beratement)


@app.route("/register", methods=["GET", "POST"])
def register_process():
    """Display registration form and register user in DB"""

    if request.method == 'POST':
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
    elif request.method == "GET":
        """Displays registration form"""

        return render_template("register_form.html")


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
