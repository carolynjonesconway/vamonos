from flask import Flask, redirect, render_template, flash, session, request, json, send_file
from model import *
from datetime import datetime, timedelta
import geocoder
import requests
import random
import pytz


app = Flask(__name__)
app.secret_key = environ.get('FLASK_SECRET_KEY', "SuperSecretUnguessableKey")

DEBUG = 'NO_DEBUG' not in environ
PORT = environ.get('PORT', 5000)

#############################################################
# Routes

@app.route("/login", methods=['GET'])
def login_page():
	"""Displays login page"""

	return render_template("login.html")



@app.route("/login", methods=['POST'])
def login():
	"""Logs in the user, or denies access"""

	email = request.form.get("email")
	password = request.form.get("password")
	
	user = User.authenticate(email, password)

	if user:
		session["user_id"] = user.user_id
		session["fname"] = user.fname
		return redirect("/trips")

	else:
		flash("Your information could not be found in the system. Try again or sign up!")
		return redirect("/login")



@app.route("/signup", methods=['GET'])
def signup_page():
	"""Displays signup page"""

	return render_template("signup.html")



@app.route("/signup", methods=['POST'])
def signup():
	"""Adds new user to the DB."""

	email = request.form.get("email")
	found_user = User.query.filter_by(email=email).all()

	if found_user:
		msg = "We found your email in our database. Try logging in instead!"

	else:
		# Get user info from form
		fname = request.form.get("fname")
		lname = request.form.get("lname")
		password = request.form.get("password")
		
		# Add user to DB
		user = User(fname=fname,
				   lname=lname,
				   email=email,
				   password=password,
				   )
		db.session.add(user)
		db.session.commit()

		msg = "Welcome, %s! You're now signed up. Log in to get started!" % (fname)

	flash(msg)
	return redirect("/login")



@app.route("/logout")
def logout():
	"""Logs the user out, clearing the session"""

	session.clear()
	flash("You have been successfully logged out.")
	return redirect("/")



@app.route("/user<int:user_id>/profile")
def profile(user_id):
	"""Displays a user's profile"""

	user = User.query.get(user_id)
	friends = [(friendship.friend_id, friendship.friend.fname, friendship.friend.img_url) for friendship in user.friendships]
	
	return render_template("profile.html", user=user, friends=friends)



@app.route("/add_phone", methods=['POST'])
def edit_phone():
	"""Updates the user's phone number"""

	phone = str(request.form['phone'])
	phone = '+1' + phone
	user = User.query.get(session['user_id'])

	user.phone = phone
	db.session.commit()



@app.route("/add_friend", methods=["POST"])
def add_friend():
	"""Adds a new friendship to the DB"""

	email = request.form.get("email")
	friend = User.get_by_email(email)

	if friend:
		try: # Check for an existing friendship
			Friendship.query.filter_by(admin_id=session['user_id'],
									   friend_id=friend.user_id
									   ).one()
			msg = "You were already friends with %s!" % (friend.fname)

		except NoResultFound:
			# Add friendship to the DB
			friendship = Friendship(admin_id=session['user_id'],
									friend_id=friend.user_id
									)
			db.session.add(friendship)
			db.session.commit()
			msg = "You have successfully added %s to your friends!" % (friend.fname)

	else:
		msg = "We couldn't find anyone with that email in our system."

	flash(msg)

	url = "/user%d/profile" % (session['user_id'])
	return redirect(url)



@app.route("/trips")
def trips():
	"""Displays all of a user's trips"""

	if 'user_id' in session:
		user_id = session["user_id"]
		permissions = Permission.query.filter_by(user_id=user_id).all()
		trips = [perm.trip for perm in permissions]

		return render_template("trips.html", user_id=user_id, trips=trips)
	
	else:
		flash("Sorry, you need to be logged in to do that!")
		return redirect("/login")



@app.route("/trip<int:trip_id>")
def trip_planner(trip_id):
	"""Displays trip planning page"""

	if 'user_id' in session:

		try:
			permission = Permission.query.filter_by(trip_id=trip_id, user_id=session['user_id']).one()
		except NoResultFound:
			permission = None

		if permission:
			viewer_id = session['user_id']
			trip = Trip.query.get(trip_id)
			admin_id = trip.admin_id
			permissions = Permission.query.filter(Permission.trip_id == trip_id, Permission.user_id != admin_id).all()
			friendships = Friendship.query.filter_by(admin_id = viewer_id).all()

			friends = []
			for fs in friendships:
				try:
					perm = Permission.query.filter_by(user_id=fs.friend_id, trip_id=trip_id).one()
					can_view = True

					if perm.can_edit:
						can_edit = True
					else:
						can_edit = False

				except NoResultFound:
					can_view = False
					can_edit = False

				friends.append((fs.friend.fname, fs.friend_id, can_view, can_edit))

			friend_ids = [friendship.friend_id for friendship in friendships]

			trip = Trip.query.get(trip_id)

			# Pass 'can_edit' boolean into template
			user_perm = Permission.query.filter(Permission.trip_id == trip_id,
												Permission.user_id == viewer_id
												).one()

			if user_perm.can_edit:
				can_edit = True
			else:
				can_edit = False

			# Pass 'admin' boolean into template
			if viewer_id == admin_id:
				admin = True
			else:
				admin = False

			return render_template("trip_planner.html",
									trip=trip,
									permissions=permissions,
									friends=friends,
									friend_ids=friend_ids,
									can_edit=can_edit,
									admin=admin,
									gg_browser_key=gg_browser_key,
									convert_to_tz=convert_to_tz,
									declare_tz=declare_tz
									)
		elif not permission:
			flash("Sorry, you don't have access to that trip!")
			return redirect("/trips")

	elif 'user_id' not in session:
		flash("Sorry, you need to be logged in to do that!")
		return redirect("/login")



@app.route("/edit_permission", methods=["POST"])
def edit_permission():
	"""Adds a new permission to the DB"""

	# Get info from form
	trip_id = int(request.form.get("tripId"))
	friend_id = int(request.form.get("friendId"))
	can_edit = int(request.form.get("canEdit"))

	
	if can_edit: # can_edit was 1
		can_edit = True

	else: # can_edit was 0
		can_edit = False
	
	try:
		# Check for existing permissions, update if found
		perm = Permission.query.filter(Permission.user_id == friend_id, Permission.trip_id == trip_id).one()
		perm.can_edit = can_edit

	except NoResultFound:
		# Add new permission to DB
		perm = Permission(trip_id=trip_id,
						  user_id=friend_id,
						  can_edit=can_edit
						  )
		db.session.add(perm)
	db.session.commit()

	return "Success"



@app.route("/rm_permission", methods=["POST"])
def rm_permission():
	"""Deletes a permission from the DB"""

	# Get info from form
	friend_id = request.form.get("friendId")
	trip_id = int(request.form.get("tripId"))

	# Remove permission based on info
	perm = Permission.query.filter(Permission.user_id == friend_id, Permission.trip_id == trip_id).one()

	db.session.delete(perm)
	db.session.commit()

	friend = User.query.get(friend_id)
	
	return "Success"



@app.route("/create_trip")
def create_trip():
	"""Displays a form for creating a new trip"""

	if 'user_id' in session:
		user_id = session["user_id"]
		return render_template("create_trip.html")

	else:
		flash("Sorry, you need to be logged in to do that!")
		return redirect("/login")



@app.route("/create_trip", methods=["POST"])
def new_trip():
	"""Adds a trip to the database"""

	# Get trip details from form
	title = request.form.get("title")
	destination = request.form.get("destination")

	tz_name = geocoder.timezone(destination).timeZoneId

	start_raw = request.form.get("start")
	start_dt = datetime.strptime(start_raw, "%Y-%m-%d") # naive UTC
	start_local = declare_tz(start_dt, tz_name)
	start_utc = convert_to_tz(start_local, 'utc')

	end_raw = request.form.get("end")
	end_dt = datetime.strptime(end_raw, "%Y-%m-%d")
	end_dt = find_next_day(end_dt)
	end_local = declare_tz(end_dt, tz_name)
	end_utc = convert_to_tz(end_local, 'utc')

	# Get more details from geocoder
	destination = geocoder.google(destination)
	address = destination.address
	lat = destination.lat
	lng = destination.lng
	city = destination.city
	country_code = destination.country

	# Add trip to DB
	trip = Trip(admin_id=session["user_id"],
				title=title,
				start=start_utc,
				end=end_utc,
				latitude=lat,
				longitude=lng,
				address=address,
				city=city,
				country_code=country_code,
				tz_name=tz_name
				)
	db.session.add(trip)
	db.session.commit() # Commit here so that you can retrieve the trip_id!

	# Add admin permission to DB
	perm = Permission(trip_id=trip.trip_id,
					  user_id=session["user_id"],
					  can_edit=True
					  )
	db.session.add(perm)

	# Add days to DB
	trip.create_days()

	db.session.commit()
	
	flash("Your trip has been created!")

	url = "/trip%d" % (trip.trip_id)
	return redirect(url)



@app.route("/edit_start", methods=["POST"])
def edit_start():
	"""Changes the trip start"""

	# Get info from form
	trip_id = int(request.form.get("trip_id"))
	start_raw = request.form.get("start")
	start = datetime.strptime(start_raw, "%Y-%m-%d")

	# Update DB
	trip = Trip.query.get(trip_id)

	trip.start = start
	trip.notification_sent = False
	
	db.session.commit()
	trip.update_days()

	url = "/trip%d" % (trip_id)
	return redirect(url)



@app.route("/edit_end", methods=["POST"])
def edit_end():
	"""Changes the trip end"""

	# Get info from form
	trip_id = int(request.form.get("trip_id"))
	end_raw = request.form.get("end")
	end = datetime.strptime(end_raw, "%Y-%m-%d") + timedelta(1)

	# Update DB
	trip = Trip.query.get(trip_id)

	trip.end = end

	db.session.commit()
	trip.update_days()

	url = "/trip%d" % (trip_id)
	return redirect(url)



@app.route("/create_event", methods=["POST"])
def create_event():
	"""Adds a new event to the DB"""

	# Get info from form
	trip_id = int(request.form.get("trip_id"))
	title = request.form.get("title")
	description = request.form.get("description")
	location = request.form.get("location")
	location = geocoder.google(location)

	tz_name = Trip.query.get(trip_id).tz_name
	address = location.address
	lat = location.lat
	lng = location.lng
	city = location.city
	country_code = location.country

	start_raw = request.form.get("start") # This is given to us by the user in LOCAL TIME
	start_local = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M")
	start_local = declare_tz(start_local, tz_name)
	start = convert_to_tz(start_local, 'utc')

	end_raw = request.form.get("end") # This is given to us by the user in LOCAL TIME
	end_local = datetime.strptime(end_raw, "%Y-%m-%dT%H:%M")
	end_local = declare_tz(end_local, tz_name)
	end = convert_to_tz(end_local, 'utc')

	# Determine correct day
	day = Day.query.filter(Day.trip_id == trip_id, Day.start <= start, Day.end >= start).all()

	# Add event to DB
	if day:
		day = day[0]

		event = Event(day_id=day.day_id,
					  user_id=session['user_id'],
					  title=title,
					  start=start,
					  end=end,
					  address=address,
					  latitude=lat,
					  longitude=lng,
					  city=city,
					  description=description,
					  country_code=country_code
					  )
		db.session.add(event)
		db.session.commit()
		msg = "Your event has been added to your agenda!"

	else: # if the event is outside the trip dates
		msg = "Event creation failed: These dates are outside the dates of your trip!"
	
	flash(msg)
	
	url = "/trip%d" % (trip_id)
	return redirect(url)



@app.route('/new_description', methods=['POST'])
def update_description():
	"""Updates the description of a given event"""

	event_id = request.form.get('eventId')
	new_description = request.form.get('newDescription')

	event = Event.query.get(event_id)
	event.description = new_description
	db.session.commit()

	return "Success"



@app.route("/add_event/<string:event_id>/<string:trip_id>")
def add_event(event_id, trip_id):
	"""Given an eventbrite event resource_uri, adds the event to the agenda"""

	# get event info from Eventbrite API
	event_uri = "https://www.eventbriteapi.com/v3/events/%s/?token=%s" % (event_id, eb_token)
	event = requests.get(event_uri).json()

	title = event['name']['text']
	url = event['url']
	description = event['description']['text']

	start_raw = event['start']['utc']
	start = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M:%SZ")

	end_raw = event['end']['utc']
	end = datetime.strptime(end_raw, "%Y-%m-%dT%H:%M:%SZ")

	venue_id = event['venue_id']
	venue_uri = "https://www.eventbriteapi.com/v3/venues/%s/?token=%s" % (venue_id, eb_token)
	venue = requests.get(venue_uri).json()

	place_name = venue.get('address',{}).get('name')
	address = venue['address'].get('address_1')
	city = venue['address'].get('city')
	country_code = venue['address'].get('country')
	lat = venue['latitude']
	lng = venue['longitude']

	# create the event for the DB
	trip = Trip.query.get(trip_id)
	trip_start = trip.start
	trip_end = trip.end

	# Determine correct day
	day = Day.query.filter(Day.trip_id == int(trip_id), Day.start <= start, Day.end >= start).all()

	# Add event to DB
	if day:
		day = day[0]
		event = Event(day_id=day.day_id,
					  user_id=session['user_id'],
					  title=title,
					  start=start,
					  end=end,
					  place_name=place_name,
					  address=address,
					  city=city,
					  country_code=country_code,
					  latitude=lat,
					  longitude=lng,
					  url=url,
					  description=description
					  )
		db.session.add(event)
		db.session.commit()
		print "\n\n", Event.query.all(), "\n\n"
	start = convert_to_tz(declare_tz(start, 'utc', result='aware'), trip.tz_name)
	end = convert_to_tz(declare_tz(end, 'utc', result='aware'), trip.tz_name)


	if trip.admin_id == session['user_id']:
		admin = True
	else:
		admin = False

	response_dict = {
		'user':{
			'userId':session['user_id'],
			'fname':session['fname'],
			'admin':admin
		},
		'event':{
			'dayId':event.day_id,
			'eventId':event.event_id,
			'url':event.url,
			'title':event.title,
			'address':event.address,
			'city':event.city,
			'start':start,
			'end':end,
			'description':event.description,
			'attendances':{}
		}

	}

	for att in response_dict['event']['attendances']:
		response_dict['event']['attendances'][att.attendance_id] = att.user.fname

	return json.dumps(response_dict)



@app.route("/rm_event", methods=["POST"])
def rm_event():
	"""Removes an event from the trip"""
	
	event_id = int(request.form.get("eventId"))

	event = Event.query.get(event_id)

	for att in event.attendances:
		db.session.delete(att)

	db.session.delete(event)
	db.session.commit()

	return "Success"



@app.route('/check_attendance', methods=['POST'])
def check_attendance():
	"""Checks if a user is attending a given event"""

	event_id = int(request.form.get('eventId'))
	user_id = session['user_id']

	try:
		Attendance.query.filter_by(event_id=event_id, user_id=user_id).one()
		return True
	
	except NoResultFound:
		return False


@app.route("/add_attendee", methods=['POST'])
def add_attendee():
	"""Adds an 'attendance' to the DB"""

	event_id = int(request.form.get('eventId'))
	user_id = session['user_id']

	try:
		Attendance.query.filter_by(event_id=event_id, user_id=user_id).one()

	except NoResultFound:
		att = Attendance(event_id=event_id,
						 user_id=user_id
						)
		db.session.add(att)
		db.session.commit()

	return "Success"



@app.route('/rm_attendee', methods=['POST'])
def rm_attendee():
	"""Removes an 'attendance' from the DB"""

	event_id = int(request.form.get('eventId'))
	user_id = session['user_id']

	try:
		att = Attendance.query.filter_by(event_id=event_id, user_id=user_id).one()
		db.session.delete(att)
		db.session.commit()
	except NoResultFound:
		pass

	return "Success"


@app.route("/google_token", methods=['GET','POST'])
def return_google_token():
	"""Returns the google api token"""

	token_dict = { 'googleToken': gg_browser_key }

	return json.dumps(token_dict)



@app.route("/send_text", methods=["POST", "GET"])
def send_reminders():
	"""Sends reminders to trip viewers"""

	trip_id = int(request.form['tripId'])
	trip = Trip.query.get(trip_id)

	trip.send_SMS(tw_sid, tw_token)

	return "Success"



@app.route("/pdf", methods=["POST"])
def generate_pdf():
	"""Generates a PDF of the itinerary"""

	trip_id = int(request.form['tripId'])
	trip = Trip.query.get(trip_id)
	filename = "itinerary%d.pdf" % (trip_id)
	trip.generate_itinerary(filename)

	response_dict = {'filename': filename}
	response = json.dumps(response_dict)

	return response



@app.route("/itinerary<int:trip_id>", methods=['GET', 'POST'])
def show_pdf(trip_id):
	"""Displays the PDF itinerary"""

	filename = 'itinerary%r.pdf' % (trip_id)
	itinerary = open(filename, 'rb')

	return send_file(itinerary)


@app.route("/")
def home():
	"""Displays homepage"""

	cities = ['Dubai', 'Madrid', 'Amsterdam', 'London' , 'Paris', 'Berlin', 'Venice', 'Stockholm']
	random.shuffle(cities)
	cities_sample = random.sample(cities, 4)


	cities_dict = {}
	for city in cities_sample:
		cities_dict[city] = city

	cities_json = json.dumps(cities_dict)
	
	return render_template('home.html',
							cities=cities_sample,
							citiesJSON=cities_json)



@app.route("/token")
def return_token():
	"""Returns a jsonified version of my eventbrite token"""

	token_dict = {'token': eb_token}
	return json.dumps(token_dict)

#############################################################
# Jinja Filter

@app.template_filter('datetime')
def _format_datetime(dt, format=None, trip_end=False):
	"""Formats a datetime object for display """

	if trip_end:
		dt = dt - timedelta(1)

	if format == 'time':
		dt = datetime.strftime(dt, '%-I:%M %p')
	elif format == 'date':
		dt = datetime.strftime(dt, '%b %-d, %Y')
	elif format == 'date-short':
		dt = datetime.strftime(dt, '%b %-d')
	elif format == 'datetime pretty':
		dt = datetime.strftime(dt, '%-I:%M %p, %b %d, %Y')
	else:
		dt = datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ')

	return dt


#############################################################
# Main

if __name__ == "__main__":
	connect_to_db(app)
	app.run(debug=DEBUG, port=PORT, host='0.0.0.0')
