import os
import time
from flask import Flask, request, render_template, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import *
from sqlalchemy.exc import *
import uuid

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


database_url = "postgresql://jg3645:rh5r9@104.196.175.120/postgres"
engine = create_engine(database_url)
conn = engine.connect()
app.config['SECRET_KEY'] = '123456'

@app.route('/', methods=['GET'])
def signup_page():
    return render_template('index.html')



@app.route('/profile2', methods=['POST'])
def signup():
    session.clear()
    user_id = uuid.uuid4()
    name = request.form['name']
    email = request.form['email']
    driver_license = request.form['drivelicense']
    dob = request.form['birth']
    password_hashing = generate_password_hash(request.form['password'])
    session['user_id'] = user_id
    try:
        conn.execute("insert into users(user_id, name, email, password, driver_license, birth) values(%s, %s, %s, %s, %s, %s)", user_id, name, email, password_hashing, driver_license, dob)
        conn.execute("insert into renter(renter_id, num_of_renting) values(%s, %s)", user_id, 0)
        conn.execute("insert into owner(owner_id, owner_rating, owner_rating_num) values(%s, %s, %s)", user_id, 5, 0)
        return redirect('/user/' + str(user_id))
    except IntegrityError:
        return "invalid attempt, please go backs"
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"



@app.route('/profile1', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'GET':
        return render_template('profile.html')
    else:
        email = request.form['email']
        password = request.form['password']
        try:
            cursor = conn.execute("select * from users where email = '%s'" %(email))
            record = cursor.fetchone()
            owner = conn.execute('SELECT * FROM owner WHERE owner_id = (%s)', record.user_id).fetchall()
            renter = conn.execute('SELECT * FROM renter WHERE renter_id = (%s)', record.user_id).fetchall()
            if (len(owner) == 0):
                conn.execute("insert into owner(owner_id, owner_rating, owner_rating_num) values(%s, %s, %s)", record.user_id, 5, 0)
            if (len(renter) == 0):
                conn.execute("insert into renter(renter_id, num_of_renting) values(%s, %s)", record.user_id, 0)
            session['user_id'] = record.user_id
            if check_password_hash(record['password'], password):
                return redirect('/user/' + record.user_id)
                #return render_template("profile.html")
            return "invalid attempt, please go backs"
        except Exception as e:
            print e.message
            print "fail login"
            return render_template('index.html', message = "Invalid log in information")

#home page when user successfully log in
@app.route('/user/<uid>', methods=['GET'])
def user(uid):
    try:
        #car_ad_info = conn.execute('SELECT title, description, location, ad_id, daily_price, mileages, type, make, color, availability FROM ad_car').fetchall();
        cursor = conn.execute("select ad_car.ad_id, ad_car.title, ad_car.description, ad_car.location from ad_car").fetchall()
        car_info = []
        for i in cursor:
                car_info.append([i[0], i[1], i[2], i[3]])
        return render_template("cars.html", car_info = car_info, user_id=uid)
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"


# user's profile page.
@app.route('/user/profile/<uid>', methods=['GET'])
def user_profile(uid):
    if request.method == 'GET':
        try:
            user_cursor = conn.execute(
                "select user_id, name, email, driver_license, birth from users where user_id = '%s'" % (uid)).fetchone()
            rate =  conn.execute(
                "select * from owner  where owner_id = '%s'" % (uid)).fetchone()
            number_of_renting = conn.execute(
                "select num_of_renting from renter  where renter_id = '%s'" % (uid)).fetchone()
            return render_template('profile.html', number_of_renting = number_of_renting['num_of_renting'], rate = rate['owner_rating'], rate_num = rate['owner_rating_num'], name = user_cursor['name'], date_of_birth = user_cursor['birth'], driver_license = user_cursor['driver_license'], email = user_cursor['email'], user_id=uid)

        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"


@app.route('/bookmark/ad/<ad_id>', methods=['POST', 'GET'])
def bookmark(ad_id):
    uid = session['user_id']
    try:
        mark_date = time.strftime("%x")
        owner_id = conn.execute("select owner_id from ad_car where ad_id = '%s'" %(ad_id)).fetchone()['owner_id']
        bookmark = conn.execute("SELECT * FROM bookmark WHERE ad_id = '%s' and renter_id = '%s'" % (ad_id, uid)).fetchall()
        if len(bookmark) != 0:
            return "you have already bookmarked this ad, please go back"
        conn.execute("insert into bookmark(renter_id, ad_id, owner_id, mark_date) values(%s, %s, %s, %s)", uid, ad_id, owner_id, mark_date)
        print "successfully marked"
        return redirect('/user/' + str(uid))
    except IntegrityError:
        return "already bookmarked"
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"
      
#ad_car page. It's the page where renters can rent and bookmark car ad
@app.route('/user/ad/<ad_id>', methods=['GET', 'POST', 'PUT'])
def ad_car(ad_id):
    uid = session['user_id']
    message = ""
    if request.method == 'GET':
        try:
            cursor = conn.execute("select u.name, o.owner_rating, ad.* from ad_car as ad, users as u, owner as o where ad.ad_id = '%s' and ad.owner_id = u.user_id and ad.owner_id = o.owner_id" %(ad_id))
            cursor = cursor.fetchall()
            car_info = []
            for i in cursor:
                if i[9]:
                    car_info.append([i[0], i[1], i[2], i[8], i[10], i[11], i[12], i[13]])
            return render_template("car_detail.html", car_info=car_info, user_id=uid, ad_id=ad_id, message = message)
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

    # user rent car
    elif request.method == 'POST':
        transaction_date = time.strftime("%x")
        transaction_id = uuid.uuid4()
        try:
            owner_id = conn.execute("select owner_id from ad_car where ad_id = '%s'" %(ad_id)).fetchone()['owner_id']
            if owner_id == uid:
                return "you cannot rent your own car, please go back"
            attempt = conn.execute("select transaction_id from transaction where ad_id = '%s' and renter_id = '%s'" %(ad_id, uid)).fetchone()
            if attempt is not None:
                return "you have already sent your request, please go back"
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

        # transaction_id, transaction_date, owner_id, renter_id, ad_id, accept, finish
        try:
            conn.execute("update ad_car set availability  = FALSE where ad_id = '%s'" %(ad_id))
            conn.execute("insert into transaction(transaction_id, transaction_date, owner_id, renter_id, ad_id, accept, finish) values(%s, %s, %s, %s, %s, FALSE, FALSE)", \
                         transaction_id, transaction_date, owner_id, uid, ad_id)

            cursor = conn.execute("select * from renter where renter_id = '%s'" %(uid))
            if cursor.rowcount == 0:
                conn.execute("insert into renter(renter_id, num_of_renting) values (%s, %s)", uid, 1)

                return redirect('/user/' + str(uid))

            conn.execute("update renter set num_of_renting = num_of_renting + 1 where renter_id = '%s'" %(uid))

            return redirect('/user/' + str(uid))
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

    # user bookmark ad
    elif request.method == "PUT":
        try:

            mark_date = time.strftime("%x")
            owner_id = conn.execute("select owner_id from ad_car where ad_id = '%s'" %(ad_id)).fetchone()['owner_id']
            conn.execute("insert into bookmark(renter_id, ad_id, owner_id, mark_date) values(%s, %s, %s, %s)", uid, ad_id, owner_id, mark_date)
            #return "successfully marked"
            return redirect('/user/' + str(uid))
        except IntegrityError:
            return "already bookmarked"
        except Exception as e:
            print e.message
            return "fail bookmark"


#user's ad car page.
@app.route('/user/profile/<uid>/ad', methods=['GET', 'POST', 'DELETE'])
def user_ad_car(uid):
    message = ""
    if request.method == 'GET':
        try:
            cursor = conn.execute("select ad_car.ad_id, ad_car.title, ad_car.description, ad_car.location from ad_car where owner_id = '%s'" %(uid)).fetchall()
            car_info = []
            for i in cursor:
                car_info.append([i[0], i[1], i[2], i[3]])

            return render_template("user_post.html", car_info=car_info, user_id=uid, message = message)
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

    # user post car ad
    elif request.method == 'POST':
        ad_id = uuid.uuid4()
        owner_id = uid
        title, car_type, car_make, car_color, car_mile, car_plate_num, location, description, car_price = request.form['title'], request.form['type'], request.form['make'], request.form['color'], request.form['mile'], request.form['plate'],  request.form['local'], request.form['description'], request.form['price']
        ad_id = str(ad_id)
        try:
            conn.execute("insert into ad_car(ad_id, description, title, location, owner_id, plate_number, daily_price, availability, type, make, mileages, color) \
                          values(%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s)", ad_id, description, title, \
                          location, owner_id, car_plate_num, car_price, car_type, car_make, car_mile, car_color)
            cursor = conn.execute("select * from owner where owner_id = '%s'" %(uid))
            if cursor.rowcount == 0:
                conn.execute("insert into owner(owner_id, owner_rating, owner_rating_num) values(%s, %s, %s)", uid, 3, 0)
            cursor = conn.execute("select ad_car.ad_id, ad_car.title, ad_car.description, ad_car.location from ad_car where owner_id = '%s'" %(uid)).fetchall()
            car_info = []
            for i in cursor:
                car_info.append([i[0], i[1], i[2], i[3]])
            message = "successfully post car ad"
            return render_template("user_post.html", car_info=car_info, user_id=uid, message = message)
            
#         except IntegrityError:
#             return "invalid input(price > 0 && mileages > 0), try again"
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

    # user delete car ad
    else:
        ad_id = request.form['ad_id']
        try:
            conn.execute("delete from ad_car where ad_id = '%s'" %(ad_id))
            return "successfully delete car ad"
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"


# user's bookmark page
@app.route('/user/profile/<uid>/bookmark', methods=['GET', 'PUT'])
def user_bookmark(uid):
    # show user's bookmark car ad
    if request.method == 'GET':
        try:
            cursor = conn.execute("select b.mark_date, ad.ad_id, ad.title, ad.description, ad.location from bookmark as b, ad_car as ad where b.renter_id = '%s' and b.ad_id = ad.ad_id" % (uid)).fetchall()
            bookmark = []
            for i in cursor:
                bookmark.append([i[2], i[3], i[4], i[0], i[2]])
            return render_template("bookmark.html", bookmark = bookmark, user_id=uid)
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"

    # user unbookmark car ad
    else:
        ad_id = request.form['ad_id']
        try:
            conn.execute("delete from bookmark where renter_id = '%s' and ad_id = '%s'" %(uid, ad_id))
            return "successfully unbookmarked"
        except Exception as e:
            print e.message
            return "invalid attempt, please go backs"


# users's transaction page
@app.route('/user/profile/<uid>/transaction', methods=['GET'])
def user_transaction(uid):
    # show user's transaction page
    message = ""
    try:
        cursor = conn.execute("select t.*, ad.title, ad.description, ad.location, ad.ad_id from transaction as t, ad_car as ad where (t.renter_id = '%s' or t.owner_id = '%s') and t.ad_id = ad.ad_id" % (uid, uid))
        cursor = cursor.fetchall()
        unaccepted = []
        unfinished = []
        finished = []
        unrated = []
        for i in cursor:
            if i[2] == uid:
                if not i[5]:
                    unaccepted.append([i[0], i[2], i[3], i[1], i[7], i[8], i[9], i[10]])
                elif i[5] and not i[6]:
                    unfinished.append([i[0], i[2], i[3], i[1], i[7], i[8], i[9], i[10]])
                elif i[6]:
                    finished.append([i[0], i[2], i[3], i[1], i[7], i[8], i[9], i[10]])
            elif i[3] == uid:
                if i[6]:
                    unrated.append([i[0], i[2], i[3], i[1], i[7], i[8], i[9], i[10]])
        return render_template("transaction.html", unaccepted = unaccepted, finished = finished, unfinished = unfinished, unrated = unrated, user_id=uid, message = message)
    except Exception as e:
        print e.message
        return "fail transaction page"


# owner accept transaction
@app.route('/user/profile/<uid>/transaction/<ad_id>/accept/<renter_id>', methods=['POST', 'PUT', 'GET'])
def owner_accept_transaction(uid, ad_id, renter_id):
    #ad_id = request.form['ad_id']
    #renter_id = request.form['renter_id']
    try:
        conn.execute("update transaction set accept = TRUE where owner_id = '%s' and renter_id = '%s' and ad_id = '%s'" % (uid, renter_id, ad_id))
        cursor = conn.execute("select t.*, ad.title, ad.description, ad.location from transaction as t, ad_car as ad where (t.renter_id = '%s' or t.owner_id = '%s') and t.ad_id = ad.ad_id" % (uid, uid))
        cursor = cursor.fetchall()
        
        other_request = conn.execute("select transaction_id from transaction where ad_id = '%s' and accept = '%s'" % (ad_id, False)).fetchall()
        print other_request
        if len(other_request) != 0:
             for other in other_request:
                 print "delete from transaction where transaction_id = '%s" % (other['transaction_id'])
                 other_request = conn.execute("delete from transaction where transaction_id = '%s'" % (other['transaction_id']))
        print "successfully accept"
        return redirect('/user/' + str(uid))
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"



# owner finish transaction
@app.route('/user/profile/<uid>/transaction/<ad_id>/finish/<renter_id>', methods=['GET'])
def owner_finish_transaction(uid, ad_id, renter_id):
#     ad_id = request.form['ad_id']
#     renter_id = request.form['renter_id']
    try:

        conn.execute("update transaction set finish = TRUE where owner_id = '%s' and renter_id = '%s' and ad_id = '%s'" %(uid, renter_id, ad_id))
        #conn.execute("update ad_car set availability = TRUE where ad_id = '%s'" % (ad_id))

        print "successfully finish transaction"
        return redirect('/user/' + str(uid))
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"


# renter rate owner
@app.route('/user/profile/<uid>/transaction/rate', methods=['POST'])
def renter_rate_owner(uid):
    comment_id = uuid.uuid4()
    owner_id = request.form['owner_id']
    rate = request.form['rate']
    rate_time = time.strftime("%x")
    review = request.form['description']
    try:
        cursor = conn.execute("select t.*, ad.title, ad.description, ad.location, ad.ad_id from transaction as t, ad_car as ad where (t.renter_id = '%s' or t.owner_id = '%s') and t.ad_id = ad.ad_id" % (uid, uid))
        cursor = cursor.fetchall()
        rate_set = set()
        for i in cursor:
            if i[3] == uid:
                if i[6]:
                    rate_set.add(i[2])

        if owner_id in rate_set:
            conn.execute("insert into rate_comment(comment_id, owner_id, renter_id, rate, rate_time, review) values(%s, %s, %s, %s, %s, %s)", comment_id, owner_id, uid, rate, rate_time, review)
            conn.execute("update owner set owner_rating = (owner_rating * owner_rating_num + '%s') / (owner_rating_num + 1), owner_rating_num = owner_rating_num + 1 where owner_id = '%s'" %(rate, owner_id))
            return "successfully rated, please go back"
        else:
            return "you can only rate the owner who finished at least a transaction with you, please go back"
    except IntegrityError:
        return "invalid input(rating > 0 && rating <= 5), try again"
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"


# user's comment page
@app.route('/user/profile/<uid>/comment')
def user_comment(uid):
    try:
        cursor = conn.execute("select u.name as owner_name, ucopy.name as renter_name, rc.* from users as u, users as ucopy, rate_comment as rc \
                              where (rc.owner_id = '%s' or rc.renter_id = '%s') and rc.owner_id = u.user_id and rc.renter_id = ucopy.user_id" %(uid, uid))
        cursor = cursor.fetchall()
        comment = []
        for i in cursor:
            comment.append([i[2], i[1],i[5], i[6], i[7], i[0]])
        return render_template('comment.html', comment = comment)
    except Exception as e:
        print e.message
        return "invalid attempt, please go backs"


if __name__ == '__main__':
    app.run(host = '0.0.0.0')
