from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():



    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(120), unique=True, nullable=False)
        password = db.Column(db.String(60), nullable=False)
        points = db.Column(db.Integer, default=0)
        waste_submissions = db.relationship('WasteSubmission', backref='user', lazy=True)
        products = db.relationship('Product', backref='seller', lazy=True)
        details = db.relationship('UserDetails', backref='user', lazy=True)
        is_admin = db.Column(db.Boolean, default=False)


    class UserDetails(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        full_name = db.Column(db.String(120))
        email = db.Column(db.String(120))
        phone_number = db.Column(db.String(20))
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    class WasteSubmission(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        waste_type = db.Column(db.String(255), nullable=False)
        quantity = db.Column(db.Integer, nullable=False)
        timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    class Product(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(255), nullable=False)
        description = db.Column(db.Text, nullable=False)
        price = db.Column(db.Float, nullable=False)
        is_used = db.Column(db.Boolean, default=True)
        image = db.Column(db.LargeBinary, nullable=False)
        seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    class ProductRequest(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(255), nullable=False)
        description = db.Column(db.Text, nullable=False)
        price = db.Column(db.Float, nullable=False)
        is_used = db.Column(db.Boolean, default=True)
        image = db.Column(db.LargeBinary, nullable=False)
        seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        is_approved = db.Column(db.Boolean, default=False)


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()

            if user and user.password == password:
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('home'))

            flash('Login failed. Check your username and password.', 'danger')

        return render_template('login.html')


    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('home'))


    @app.route('/')
    def home():
        products = Product.query.all()
        return render_template('home.html', products=products)



    @app.route('/submit_waste', methods=['GET', 'POST'])
    @login_required
    def submit_waste():
        if request.method == 'POST':
            waste_type = request.form['waste_type']
            quantity = int(request.form['quantity'])

            # Calculate points based on waste submission (replace this with your logic)
            points_earned = calculate_points(waste_type, quantity)

            # Update user points
            current_user.points += points_earned
            db.session.add(WasteSubmission(waste_type=waste_type, quantity=quantity, user=current_user))
            db.session.commit()

            return redirect(url_for('home'))

        return render_template('submit_waste.html')


    @app.route('/sell_product', methods=['GET', 'POST'])
    @login_required
    def sell_product():
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            is_used = 'is_used' in request.form
            image_data = request.files['image'].read()  # Read image data as binary
            product_request = ProductRequest(
                name=name,
                description=description,
                price=price,
                is_used=is_used,
                image=image_data,
                seller=current_user
            )
            db.session.add(product_request)
            db.session.commit()

            return redirect(url_for('home'))

        return render_template('sell_product.html')


    @app.route('/admin/requests')
    @login_required
    def admin_requests():
        if not current_user.is_admin:
            flash('You do not have permission to view this page.', 'danger')
            return redirect(url_for('home'))

        # Get product requests from sellers
        product_requests = ProductRequest.query.filter_by(is_approved=False).all()
        return render_template('admin_requests.html', product_requests=product_requests)


    @app.route('/admin/approve_product/<int:product_request_id>')
    @login_required
    def admin_approve_product(product_request_id):
        if not current_user.is_admin:
            flash('You do not have permission to perform this action.', 'danger')
            return redirect(url_for('home'))

        product_request = ProductRequest.query.get_or_404(product_request_id)
        product = Product(
            name=product_request.name,
            description=product_request.description,
            price=product_request.price,
            is_used=product_request.is_used,
            image=product_request.image,
            seller=product_request.seller
        )
        db.session.add(product)
        db.session.delete(product_request)  # Remove the product request
        db.session.commit()

        flash(f'Product "{product.name}" approved successfully!', 'success')
        return redirect(url_for('admin_requests'))


    def calculate_points(waste_type, quantity):
        base_points = quantity
        if waste_type == 'plastic':
            base_points *= 2  # Double points for plastic waste
        elif waste_type == 'bio':
            base_points *= 1.5  # Bonus points for bio waste
        return int(base_points)

    def buy_product(product_id):
        product = Product.query.get_or_404(product_id)

        if request.method == 'POST':
            if current_user.points >= product.price:
                # Deduct points from the buyer
                current_user.points -= product.price
                # Add points to the seller (optional)
                product.seller.points += product.price
                # Update the database
                db.session.commit()

                flash(f'Successfully purchased {product.name}!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Insufficient points to buy this product!', 'danger')

        return render_template('buy_product.html', product=product)

    if __name__ == '__main__':
        db.create_all()
        app.run(debug=True)
