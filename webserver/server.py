import os
import time
from flask import Flask, request, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import *
from sqlalchemy.exc import *
import uuid

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


database_url = ''
engine = create_engine(database_url)
conn = engine.connect()





@app.route('/', methods=['GET'])
def signup_page():
	return render_template('signup.html')


@app.route('/signup', methods=['POST'])
def signup():
	user_id = uuid.uuid4()
	name = request.form['name']
	email = request.form['email']
	driver_license = request.form['driver_license']
	dob = request.form['dob']
	password_hashing = generate_password_hash(request.form['password'])
	try:
		conn.execute("insert into users(user_id, name, email, password, driver_license, birth) values(%s, %s, %s, %s, %s, %s)", user_id, name, email, password_hashing, driver_license, dob)
		return "success"
	except IntegrityError:
		return "email already exists"
	except Exception as e:
		print e.message
		return "fail"


@app.route('/signin', methods=['GET', 'POST'])
def signin():
	if request.method == 'GET':
		return render_template('signin.html')
	else:
		email = request.form['email']
		password = request.form['password']
		try:
			cursor = conn.execute("select * from users where email = '%s'" %(email))
			record = cursor.fetchone()
			if check_password_hash(record['password'], password):
				return redirect('/user/' + record.user_id)
			return "email and password not match"
		except Exception as e:
			print e.message
			return "fail"


#home page when user successfully log in
@app.route('/user/<uid>', methods=['GET'])
def user(uid):
	try:
		cursor = conn.execute("select ad_car.ad_id, ad_car.title, ad_car.description, ad_car.location from ad_car")
		return render_template("user.html", data=cursor.fetchall(), user_id=uid)
	except Exception as e:
		print e.message
		return "fail"


# user's profile page.
@app.route('/user/profile/<uid>', methods=['GET', 'PUT'])
def user_profile(uid):
	if request.method == 'GET':
		try:
			user_cursor = conn.execute(
				"select user_id, name, email, driver_license, birth from users where user_id = '%s'" % (uid))
			return render_template('user_profile.html', data=user_cursor.fetchone(), user_id=uid)

		except Exception as e:
			print e.message
			return "fail"

	# users modify their information
	else:
		name = request.form['name']
		dob = request.form['dob']
		driver_license = request.form['driver_license']
		try:
			conn.execute("update users set name = '%s', birth = '%s', driver_license = '%s' where user_id = '%s'" %(name, dob, driver_license, uid))
			return "successfully updated"
		except Exception as e:
			print e.message
			return "fail"


#ad_car page. It's the page where renters can rent and bookmark car ad
@app.route('/user/<uid>/ad/<ad_id>', methods=['GET', 'POST', 'PUT'])
def ad_car(uid, ad_id):
	if request.method == 'GET':
		try:
			cursor = conn.execute("select u.name, o.owner_rating, ad.*, from ad_car as ad, users as u, owner as o where ad.ad_id = '%s' and ad.owner_id = u.user_id and ad.owner_id = o.owner_id" %(ad_id))
			return render_template("ad_car.html", data=cursor.fetchall(), user_id=uid, ad_id=ad_id)
		except Exception as e:
			print e.message
			return "fail"

	# user rent car
	elif request.method == 'POST':
		transaction_date = time.strftime("%x")
		transaction_id = uuid.uuid4()
		try:
			owner_id = conn.execute("select owner_id from ad_car where ad_id = '%s'" %(ad_id)).fetchone()['owner_id']
		except Exception as e:
			print e.message
			return "fail"

		# transaction_id, transaction_date, owner_id, renter_id, ad_id, accept, finish
		try:
			conn.execute("update ad_car set available = FALSE where ad_id = '%s'" %(ad_id))
			conn.execute("insert into transaction(transaction_id, transaction_date, owner_id, renter_id, ad_id, accept, finish) values(%s, %s, %s, %s, %s, FALSE, FALSE)", \
						 transaction_id, transaction_date, owner_id, uid, ad_id)

			cursor = conn.execute("select * from renter where renter_id = '%s'" %(uid))
			if cursor.rowcount == 0:
				conn.execute("insert into renter(renter_id, num_of_renting) values (%s, %s)", uid, 1)
				return "rent success"

			conn.execute("update renter set num_of_renting = num_of_renting + 1 where renter_id = '%s'" %(uid))
			return "rent success"
		except Exception as e:
			print e.message
			return "fail"

	# user bookmark ad
	else:
		try:
			mark_date = time.strftime("%x")
			owner_id = conn.execute("select owner_id from ad_car where ad_id = '%s'" %(ad_id)).fetchone()['owner_id']
			conn.execute("insert into bookmark(renter_id, ad_id, owner_id, mark_date) values(%s, %s, %s, %s)", uid, ad_id, owner_id, mark_date)
			return "successfully marked"
		except IntegrityError:
			return "already bookmarked"
		except Exception as e:
			print e.message
			return "fail"


#user's ad car page.
@app.route('/user/profile/<uid>/ad', methods=['GET', 'POST', 'DELETE'])
def user_ad_car(uid):
	if request.method == 'GET':
		try:
			cursor = conn.execute("select ad_car.ad_id, ad_car.title, ad_car.description, ad_car.location from ad_car where owner_id = '%s'" %(uid))
			return render_template("user_ad_car.html", data=cursor.fetchall(), user_id=uid)
		except Exception as e:
			print e.message
			return "fail"

	# user post car ad
	elif request.method == 'POST':
		ad_id = uuid.uuid4()
		owner_id = uid
		title = request.form['title']
		description = request.form['description']
		location = request.form['location']
		car_type = request.form['car_type']
		car_color = request.form['car_color']
		car_make = request.form['car_make']
		car_price = request.form['car_price']
		car_mile = request.form['car_mile']
		car_plate_num = request.form['car_plate_num']
		try:
			conn.execute("insert into ad_car(ad_id, description, title, location, owner_id, plate_number, daily_price, available, type, make, mileages, color) \
						  values(%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s)", ad_id, description, title, \
						  location, owner_id, car_plate_num, car_price, car_type, car_make, car_mile, car_color)

			cursor = conn.execute("select * from owner where owner_id = '%s'" %(uid))
			if cursor.rowcount == 0:
				conn.execute("insert into owner(owner_id, owner_rating, owner_rating_num) values(%s, %s, %s)", uid, 3, 0)
			return "successfully post car ad"

		except IntegrityError:
			return "invalid input(price > 0 && mileages > 0), try again"
		except Exception as e:
			print e.message
			return "fail"

	# user delete car ad
	else:
		ad_id = request.form['ad_id']
		try:
			conn.execute("delete from ad_car where ad_id = '%s'" %(ad_id))
			return "successfully delete car ad"
		except Exception as e:
			print e.message
			return "fail"


# user's bookmark page
@app.route('/user/profile/<uid>/bookmark', methods=['GET', 'PUT'])
def user_bookmark(uid):
	# show user's bookmark car ad
	if request.method == 'GET':
		try:
			cursor = conn.execute("select b.mark_date, ad.ad_id, ad.title, ad.description, ad.location from bookmark as b, ad_car as ad where b.renter_id = '%s' and b.ad_id = ad.ad_id" % (uid))
			print cursor.fetchall()
			return render_template("user_bookmark.html", data=cursor.fetchall(), user_id=uid)
		except Exception as e:
			print e.message
			return "fail"

	# user unbookmark car ad
	else:
		ad_id = request.form['ad_id']
		try:
			conn.execute("delete from bookmark where renter_id = '%s' and ad_id = '%s'" %(uid, ad_id))
			return "successfully unbookmarked"
		except Exception as e:
			print e.message
			return "fail"


# users's transaction page
@app.route('/user/profile/<uid>/transaction', methods=['GET'])
def user_transaction(uid):
	# show user's transaction page
	try:
		cursor = conn.execute("select t.*, ad.title, ad.description, ad.location from transaction as t, ad_car as ad where (t.renter_id = '%s' or t.owner_id = '%s') and t.ad_id = ad.ad_id" % (uid, uid))
		return render_template("user_transaction.html", data=cursor.fetchall(), user_id=uid)
	except Exception as e:
		print e.message
		return "fail"


# owner accept transaction
@app.route('/user/profile/<uid>/transaction/accept', methods=['PUT'])
def owner_accept_transaction(uid):
	ad_id = request.form['ad_id']
	renter_id = request.form['renter_id']
	try:
		conn.execute("update transaction set accept = TRUE where owner_id = '%s' and renter_id = '%s' and ad_id = '%s'" %(uid, renter_id, ad_id))
		return "successfully accept"
	except Exception as e:
		print e.message
		return "fail"



# owner finish transaction
@app.route('/user/profile/<uid>/transaction/finish', methods=['PUT'])
def owner_finish_transaction(uid):
	ad_id = request.form['ad_id']
	renter_id = request.form['renter_id']
	try:
		conn.execute("update transaction set finish = TRUE where owner_id = '%s' and renter_id = '%s' and ad_id = '%s'" %(uid, renter_id, ad_id))
		conn.execute("update ad_car set available = TRUE where ad_id = '%s'" % (ad_id))
		return "successfully finish transaction"
	except Exception as e:
		print e.message
		return "fail"


# renter rate owner
@app.route('/user/profile/<uid>/transaction/rate', methods=['POST'])
def renter_rate_owner(uid):
	comment_id = uuid.uuid4()
	owner_id = request.form['owner_id']
	rate = request.form['rate']
	rate_time = time.strftime("%x")
	review = request.form['review']
	try:
		conn.execute("insert into rate_comment(comment_id, owner_id, renter_id, rate, rate_time, review) values(%s, %s, %s, %s, %s, %s)", comment_id, owner_id, uid, rate, rate_time, review)
		conn.execute("update owner set owner_rating = (owner_rating * owner_rating_num + '%s') / (owner_rating_num + 1), owner_rating_num = owner_rating_num + 1 where owner_id = '%s'" %(rate, owner_id))
		return "successfully rated"

	except IntegrityError:
		return "invalid input(rating > 0 && rating <= 5), try again"
	except Exception as e:
		print e.message
		return "fail"


# user's comment page
@app.route('/user/profile/<uid>/comment')
def user_comment(uid):
	try:
		cursor = conn.execute("select u.name as owner_name, ucopy.name as renter_name, rc.* from users as u, users as ucopy, rate_comment as rc \
							  where (rc.owner_id = '%s' or rc.renter_id = '%s') and rc.owner_id = u.user_id and rc.renter_id = ucopy.user_id" %(uid, uid))
		return render_template('user_comment.html', cursor.fetchall())
	except Exception as e:
		print e.message
		return "fail"


if __name__ == '__main__':
	app.run()
