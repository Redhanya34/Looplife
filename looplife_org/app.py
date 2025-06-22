from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abcd'  # Replace with a secure key

# Clever Cloud MySQL config
app.config['MYSQL_HOST'] = 'bsgowou9jku2ueu4w8ef-mysql.services.clever-cloud.com'
app.config['MYSQL_USER'] = 'ud0cqifyqro6rou4'
app.config['MYSQL_PASSWORD'] = 'nGy3nec11yaXR45Q6Dyh'
app.config['MYSQL_DB'] = 'bsgowou9jku2ueu4w8ef'

# Connection setup
mysql = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB'],
    port=3306,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, points=0, weight= 0,is_admin=False):
        self.id = id
        self.username = username
        self.password = password
        self.points = points
        self.weight =weight
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(id):
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user_data = cursor.fetchone()
    if user_data:
        return User(**user_data)
    return None

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Additional registration logic here, such as checking if the username is already taken
        cursor = mysql.cursor()
        cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', (username, password))
        mysql.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
        user_data = cursor.fetchone()

        if user_data and user_data['password'] == password:
            user = User(**user_data)
            login_user(user)
            flash('Logged in successfully.', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))

        flash('Login failed. Check your username and password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))


@app.route('/user/dashboard')
@login_required
def user_dashboard():
    user_waste_submissions = get_user_waste_submissions(current_user.id)
    return render_template('user_dashboard.html', user=current_user, waste_submissions=user_waste_submissions)
@app.route('/user/sell_product', methods=['GET', 'POST'])
@login_required
def user_sell_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        
        # Check if the file is included in the request
        if 'image' in request.files:
            image_data = request.files['image'].read()
            add_product_to_database(name, description, price, image_data, current_user.id)
            flash('Product added successfully.', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Please include an image of the product.', 'danger')
            return redirect(request.url)  # Redirect back to the same page
        
    return render_template('sell_product.html')

def add_product_to_database(name, description, price, image, seller_id):
    cursor = mysql.cursor()
    cursor.execute('INSERT INTO product (name, description, price, image, seller_id) VALUES (%s, %s, %s, %s, %s)',
                   (name, description, price, image, seller_id))
    mysql.commit()


@app.route('/user/buy_products')
@login_required
def user_buy_products():
    products = get_all_products()
    return render_template('buy_product.html', user=current_user, products=products)

@app.route('/user/buy_product')
@login_required
def user_buy_product():
    product = get_product_by_id()

    if product:
        if current_user.points >= product['price']:
            current_user.points -= product['price']
            update_user_points(current_user.id, current_user.points)
            flash(f'Product "{product["name"]}" purchased successfully!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Insufficient points to buy this product!', 'danger')

    return redirect(url_for('user_buy_products'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('home'))

    all_users = get_all_users()
    all_waste_submissions = get_all_waste_submissions()
    return render_template('admin_dashboard.html', users=all_users, waste_submissions=all_waste_submissions)

@app.route('/admin/update_page')
@login_required
def admin_update_page():
    return render_template('admin_update_page.html')

@app.route('/admin/update_weights_and_rewards', methods=['POST'])
@login_required
def admin_update_weights_and_rewards():
    customer_name = request.form['customer_name']
    weight = float(request.form.get('weight', 0)) 

    # Fetch user details
    user_details = get_user_details(customer_name)

    if user_details:
        # Calculate reward points based on the weight (adjust the calculation as needed)
        reward_points = int(weight * 0.1)  # Adjust the multiplier as needed

        # Update user weight and points
        update_user_weight_and_rewards(user_details['username'], weight, reward_points)

        flash('Weights and rewards updated successfully.', 'success')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('admin_dashboard'))

def get_user_details(username):
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
    user_details = cursor.fetchone()
    return user_details

def update_user_weight_and_rewards(username, weight, reward_points):
    cursor = mysql.cursor()
    cursor.execute('UPDATE user SET weight = %s, points = points + %s WHERE username = %s', (weight, reward_points, username))
    mysql.commit()


# @app.route('/admin/update_weights_and_rewards_new', methods=['POST'])
# @login_required
# def admin_update_weights_and_rewards_new():
#     customer_name = request.form.get('customer_name')
#     new_weight = float(request.form['new_weight'])

#     # Calculate reward points based on the weight (adjust the calculation as needed)
#     reward_points = int(new_weight * 0.1)  # Adjust the multiplier as needed

#     # Update user weight and points
#     update_user_weight_and_rewards(customer_name, new_weight, reward_points)

#     flash('Weights and rewards updated successfully.', 'success')
#     return redirect(url_for('admin_dashboard'))

def get_all_products():
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM product')
    products = cursor.fetchall()
    return products

def get_user_waste_submissions(id):
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM wastesubmission WHERE user_id = %s', (id,))
    waste_submissions = cursor.fetchall()
    return waste_submissions

def add_product_request(name, description, price, image, seller_id):
    cursor = mysql.cursor()
    cursor.execute('INSERT INTO productrequest (name, description, price, image, seller_id) VALUES (%s, %s, %s, %s, %s)',
                   (name, description, price, image, seller_id))
    mysql.commit()

def get_all_users():
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM user')
    users = cursor.fetchall()
    return users

def get_all_waste_submissions():
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM wastesubmission')
    waste_submissions = cursor.fetchall()
    return waste_submissions

def get_product_by_id():
    cursor = mysql.cursor()
    cursor.execute('SELECT * FROM product')
    product = cursor.fetchone()
    return product

def update_user_points(id, new_points):
    cursor = mysql.cursor()
    cursor.execute('UPDATE user SET points = %s WHERE user_id = %s', (new_points, id))
    mysql.commit()

def update_user_weight(id, weight):
    cursor = mysql.cursor()
    cursor.execute('UPDATE user SET weight = %s WHERE user_id = %s', (weight, id))
    mysql.commit()

# def update_user_weight_and_rewards(username, new_weight, reward_points):
#     cursor = mysql.cursor()
#     cursor.execute('UPDATE user SET weight = %s, points = points + %s WHERE username = %s', (new_weight, reward_points, username))
#     mysql.commit()

if __name__ == '__main__':
    app.run(debug=True)
