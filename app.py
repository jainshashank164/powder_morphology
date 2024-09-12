from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
db = SQLAlchemy(app)

# Ensure uploads directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Define ImageUpload model
class ImageUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    batch_number = db.Column(db.String(100), nullable=False)
    powder_type = db.Column(db.String(100), nullable=False)
    image_path = db.Column(db.String(150), nullable=False)
    cycle_number = db.Column(db.String(100))
    predicted_value = db.Column(db.Float)
    user = db.relationship('User', backref=db.backref('images', lazy=True))

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'initial_image' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['initial_image']
        batch_number = request.form.get('batch_number')
        powder_type = request.form.get('powder_type')

        if not file or file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if not batch_number or not powder_type:
            flash('Batch number and powder type are required.')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Store initial image details in the database
            initial_image = ImageUpload(
                user_id=session.get('user_id'),
                batch_number=batch_number,
                powder_type=powder_type,
                image_path=filename,
                cycle_number=None,
                predicted_value=None
            )
            db.session.add(initial_image)
            db.session.commit()

            # Store the initial image ID in the session for later use
            session['initial_image_id'] = initial_image.id

            flash('Initial image uploaded successfully!', 'success')
            return redirect(url_for('upload_new'))

    return render_template('index.html')

@app.route('/upload_new', methods=['GET', 'POST'])
def upload_new():
    initial_image_id = session.get('initial_image_id')
    initial_image = ImageUpload.query.get(initial_image_id)

    if request.method == 'POST':
        if 'new_image' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['new_image']
        batch_number = initial_image.batch_number if initial_image else request.form.get('batch_number')
        powder_type = initial_image.powder_type if initial_image else request.form.get('powder_type')
        cycle_number = request.form.get('cycle_number')

        if not file or file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if not cycle_number:
            flash('Cycle number is required.')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Here you would use your model to compare images and get the predicted value
            predicted_value = 0.0  # Placeholder for actual prediction result

            # Store new image details and comparison results in the database
            new_image = ImageUpload(
                user_id=session.get('user_id'),
                batch_number=batch_number,
                powder_type=powder_type,
                image_path=filename,
                cycle_number=cycle_number,
                predicted_value=predicted_value
            )
            db.session.add(new_image)
            db.session.commit()

            flash('New image uploaded and compared successfully!', 'success')
            return redirect(url_for('results', initial_image_id=initial_image.id))

    return render_template('upload_new.html', batch_number=initial_image.batch_number if initial_image else '', powder_type=initial_image.powder_type if initial_image else '')


@app.route('/results/<int:initial_image_id>', methods=['GET'])
def results(initial_image_id):
    initial_image = ImageUpload.query.get(initial_image_id)
    if not initial_image:
        flash('Initial image not found.', 'error')
        return redirect(url_for('index'))

    # Retrieve all new images compared with the initial image
    compared_images = ImageUpload.query.filter_by(user_id=session.get('user_id'), batch_number=initial_image.batch_number).all()

    return render_template('results.html', initial_image=initial_image, compared_images=compared_images)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect username or password. Please try again or register.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
