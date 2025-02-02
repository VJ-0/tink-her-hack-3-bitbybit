from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session  # Session management
import sqlite3

# Initialize Flask app
app = Flask(__name__)

# App configuration for session
app.config['SECRET_KEY'] = 'your_secret_key'  # Required for session management
app.config['SESSION_TYPE'] = 'filesystem'  # Store session data in the filesystem
Session(app)

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('clique.db')  # SQLite database file
    conn.row_factory = sqlite3.Row  # Allow column access via keys
    return conn

# Initialize the database with required tables
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            bio TEXT
        )
    ''')

    # Create friend_requests table
    c.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT CHECK(status IN ('pending', 'accepted', 'rejected')),
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize database when the app starts
init_db()

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists and password is correct
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True  # Keep session active
            flash("Login successful!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password.", "error")
    
    return render_template('login.html')

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash("Registration successful, please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different one.", "error")
        finally:
            conn.close()
    
    return render_template('register.html')

# Route for the user's profile page
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    return render_template('profile.html', user=user)

# Route to send a friend request
@app.route('/send_friend_request', methods=['POST'])
@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login page
    
    sender_id = session['user_id']
    receiver_username = request.form['receiver_username']
    
    # Look for the receiver user by username
    conn = get_db_connection()
    receiver = conn.execute('SELECT * FROM users WHERE username = ?', (receiver_username,)).fetchone()
    
    if receiver:
        # Insert friend request into the database (pending status)
        conn.execute('INSERT INTO friend_requests (sender_id, receiver_id, status) VALUES (?, ?, ?)', 
                     (sender_id, receiver['id'], 'pending'))
        conn.commit()
        flash("Friend request sent!", "success")
    else:
        flash("User not found.", "error")
    
    conn.close()
    return redirect(url_for('profile'))  # Redirect back to profile page


# Route to view all friend requests
@app.route('/friend_requests')
def friend_requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login page
    
    user_id = session['user_id']
    
    # Get all pending friend requests for the logged-in user
    conn = get_db_connection()
    requests = conn.execute('SELECT * FROM friend_requests WHERE receiver_id = ? AND status = "pending"', 
                            (user_id,)).fetchall()
    conn.close()
    
    return render_template('friend_requests.html', requests=requests)
# Route to accept a friend request
@app.route('/accept_friend_request/<int:sender_id>')
def accept_friend_request(sender_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login page
    
    user_id = session['user_id']
    
    # Update the friend request status to accepted
    conn = get_db_connection()
    conn.execute('UPDATE friend_requests SET status = "accepted" WHERE sender_id = ? AND receiver_id = ?',
                 (sender_id, user_id))
    conn.commit()
    conn.close()
    
    flash("Friend request accepted!", "success")
    return redirect(url_for('friend_requests'))  # Redirect to friend requests page

# Route for logging out
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Run Flask app on a local network
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)  # Try default port
    except OSError:
        app.run(host="0.0.0.0", port=8080, debug=True)  # Use 8080 if 5000 is busy
