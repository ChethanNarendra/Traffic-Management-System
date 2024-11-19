from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages and sessions

# Add these configurations
UPLOAD_FOLDER = 'static/vehicle_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Chethan@24",
        database="TrafficManagementSystem"
    )

# Add this route at the beginning of your routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE Email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['Password'], password):
            session['user_id'] = user['UserID']
            session['user_name'] = user['Name']
            session['role'] = user['Role']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
        return redirect(url_for('login'))
    return render_template('login.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Get violation statistics (only for active violations)
    cursor.execute("""
        SELECT 
            Status,
            COUNT(*) as count,
            SUM(FineAmount) as total_amount
        FROM TrafficViolations
        WHERE Status != 'Cancelled' OR Status IS NULL
        GROUP BY Status
    """)
    stats = cursor.fetchall()
    
    # Get recent violations (only active ones)
    cursor.execute("""
        SELECT 
            v.*,
            veh.RegistrationNumber,
            o.Name as OfficerName
        FROM TrafficViolations v
        JOIN Vehicles veh ON v.VehicleID = veh.VehicleID
        LEFT JOIN Officers o ON v.OfficerID = o.OfficerID
        WHERE v.Status != 'Cancelled' OR v.Status IS NULL
        ORDER BY v.CreatedAt DESC
        LIMIT 10
    """)
    violations = cursor.fetchall()
    
    db.close()
    return render_template('dashboard.html', violations=violations, stats=stats)

# Violations route
@app.route('/violations', methods=['GET', 'POST'])
def violations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Handle both vehicle registration and violation recording
    if request.method == 'POST':
        if 'registration_number' in request.form:  # Vehicle registration form
            try:
                image_path = None
                if 'vehicle_image' in request.files:
                    file = request.files['vehicle_image']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Add timestamp to filename to make it unique
                        filename = f"{int(time.time())}_{filename}"
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_path = filename

                cursor.execute("""
                    INSERT INTO Vehicles (
                        RegistrationNumber, Type, Make, Model, 
                        OwnerName, OwnerPhone, OwnerAddress, ImagePath
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    request.form['registration_number'],
                    request.form['vehicle_type'],
                    request.form['make'],
                    request.form['model'],
                    request.form['owner_name'],
                    request.form['owner_phone'],
                    request.form['owner_address'],
                    image_path
                ))
                db.commit()
                flash('Vehicle registered successfully')
            except Exception as e:
                db.rollback()
                flash(f'Error registering vehicle: {str(e)}')
        else:  # Violation recording form
            vehicle_reg = request.form['vehicle_reg']
            violation_type = request.form['violation_type']
            fine_amount = request.form['fine_amount']
            officer_id = request.form['officer_id']
            
            try:
                # First get the vehicle ID
                cursor.execute("SELECT VehicleID FROM Vehicles WHERE RegistrationNumber = %s", (vehicle_reg,))
                vehicle = cursor.fetchone()
                
                if vehicle:
                    cursor.execute("""
                        INSERT INTO TrafficViolations 
                        (VehicleID, ViolationType, FineAmount, OfficerID)
                        VALUES (%s, %s, %s, %s)
                    """, (vehicle['VehicleID'], violation_type, fine_amount, officer_id))
                    db.commit()
                    flash('Violation recorded successfully')
                else:
                    flash('Vehicle not found. Please check the registration number.')
            except Exception as e:
                db.rollback()
                flash(f'Error recording violation: {str(e)}')
    
    # Fetch officers for the dropdown
    cursor.execute("SELECT * FROM Officers WHERE Status = 'Active'")
    officers = cursor.fetchall()
    
    # Fetch violations
    cursor.execute("""
        SELECT v.*, veh.RegistrationNumber, veh.Make, veh.Model,
               veh.OwnerName, veh.OwnerPhone, o.Name as OfficerName
        FROM TrafficViolations v
        JOIN Vehicles veh ON v.VehicleID = veh.VehicleID
        LEFT JOIN Officers o ON v.OfficerID = o.OfficerID
        ORDER BY v.CreatedAt DESC
    """)
    violations = cursor.fetchall()
    
    # Fetch vehicles with violation count
    cursor.execute("""
        SELECT v.*, 
               (SELECT COUNT(*) FROM TrafficViolations tv WHERE tv.VehicleID = v.VehicleID) as ViolationCount
        FROM Vehicles v
        ORDER BY v.RegistrationNumber
    """)
    vehicles = cursor.fetchall()
    
    db.close()
    return render_template('violations.html', 
                         violations=violations, 
                         officers=officers, 
                         vehicles=vehicles)

# Add this new route for logout
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))

# function to create a test user
def create_test_user():
    db = get_db_connection()
    cursor = db.cursor()
    
    # Check if test user already exists
    cursor.execute("SELECT * FROM Users WHERE Email = 'admin@test.com'")
    if cursor.fetchone() is not None:
        print("Test user already exists!")
        return
    
    # Create a simple password hash
    password = "admin123"
    hashed_password = generate_password_hash(password)
    
    try:
        cursor.execute("""
            INSERT INTO Users (Name, Role, Email, Password, IsActive)
            VALUES (%s, %s, %s, %s, TRUE)
        """, ('Admin User', 'Administrator', 'admin@test.com', hashed_password))
        db.commit()
        print("Test user created successfully!")
        print("Email: admin@test.com")
        print("Password: admin123")
    except Exception as e:
        print(f"Error creating test user: {e}")
    finally:
        cursor.close()
        db.close()

@app.route('/delete_violation/<int:violation_id>', methods=['POST'])
def delete_violation(violation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("DELETE FROM TrafficViolations WHERE ViolationID = %s", (violation_id,))
        db.commit()
        flash('Violation deleted successfully')
    except Exception as e:
        db.rollback()
        flash(f'Error deleting violation: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('violations'))

# Officers Management
@app.route('/officers', methods=['GET', 'POST'])
def officers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        try:
            # Update the status values to match the database constraints
            status = request.form.get('status')
            if status not in ['Active', 'Suspended', 'Retired']:
                status = 'Active'  # Default value
                
            cursor.execute("""
                INSERT INTO Officers (Name, OfficerRank, StationID, Status) 
                VALUES (%s, %s, %s, %s)
            """, (
                request.form.get('name'),
                request.form.get('rank'),
                request.form.get('police_station'),
                status
            ))
            db.commit()
            flash('Officer registered successfully')
        except Exception as e:
            db.rollback()
            flash(f'Error registering officer: {str(e)}')
    
    # Fetch police stations
    cursor.execute("SELECT * FROM PoliceStations ORDER BY Name")
    police_stations = cursor.fetchall()
    
    # Fetch officers with violation count and station information
    cursor.execute("""
        SELECT o.*, 
               ps.Name as StationName,
               (SELECT COUNT(*) FROM TrafficViolations tv WHERE tv.OfficerID = o.OfficerID) as ViolationCount
        FROM Officers o
        LEFT JOIN PoliceStations ps ON o.StationID = ps.StationID
        ORDER BY ps.Name, o.Name
    """)
    officers = cursor.fetchall()
    
    db.close()
    return render_template('officers.html', 
                         officers=officers, 
                         police_stations=police_stations)

# Stations Management
@app.route('/stations', methods=['GET', 'POST'])
def stations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        contact = request.form['contact']
        
        try:
            cursor.execute("""
                INSERT INTO PoliceStations (Name, Location, ContactNumber)
                VALUES (%s, %s, %s)
            """, (name, location, contact))
            db.commit()
            flash('Police Station added successfully')
        except Exception as e:
            db.rollback()
            flash(f'Error adding police station: {str(e)}')
    
    cursor.execute("SELECT * FROM PoliceStations ORDER BY CreatedAt DESC")
    stations = cursor.fetchall()
    db.close()
    
    return render_template('stations.html', stations=stations)

@app.route('/update_violation_status/<int:violation_id>', methods=['POST'])
def update_violation_status(violation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    status = request.form.get('status')
    if status not in ['Pending', 'Paid', 'Cancelled']:
        flash('Invalid status')
        return redirect(url_for('violations'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        if status == 'Cancelled':
            # If status is Cancelled, delete the violation instead of updating
            cursor.execute("DELETE FROM TrafficViolations WHERE ViolationID = %s", (violation_id,))
            flash('Violation cancelled and removed from records')
        else:
            # For other statuses, update normally
            cursor.execute("""
                UPDATE TrafficViolations 
                SET Status = %s 
                WHERE ViolationID = %s
            """, (status, violation_id))
            flash('Violation status updated successfully')
        
        db.commit()
    except Exception as e:
        db.rollback()
        flash(f'Error updating status: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('violations'))

@app.route('/update_officer_status/<int:officer_id>', methods=['POST'])
def update_officer_status(officer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    status = request.form.get('status')
    if status not in ['Active', 'Suspended']:
        flash('Invalid status')
        return redirect(url_for('officers'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        # First check if the officer exists
        cursor.execute("SELECT OfficerID FROM Officers WHERE OfficerID = %s", (officer_id,))
        if not cursor.fetchone():
            flash('Officer not found')
            return redirect(url_for('officers'))
        
        # Update the officer's status
        cursor.execute("""
            UPDATE Officers 
            SET Status = %s,
                UpdatedAt = NOW()
            WHERE OfficerID = %s
        """, (status, officer_id))
        
        db.commit()
        flash(f'Officer status updated to {status}')
    except Exception as e:
        db.rollback()
        flash(f'Error updating officer status: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('officers'))

@app.route('/transfer_officer/<int:officer_id>', methods=['POST'])
def transfer_officer(officer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    new_station = request.form.get('new_station')
    transfer_reason = request.form.get('transfer_reason')
    
    try:
        # Create a new connection with correct credentials
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Chethan@24',
            database='TrafficManagementSystem'
        )
        cursor = conn.cursor(dictionary=True)

        # Get current station ID
        cursor.execute("SELECT StationID FROM Officers WHERE OfficerID = %s", (officer_id,))
        result = cursor.fetchone()
        
        if not result:
            flash('Officer not found', 'error')
            return redirect(url_for('officers'))
            
        current_station = result['StationID']
        
        # Insert transfer record
        cursor.execute("""
            INSERT INTO OfficerTransfers 
            (OfficerID, FromStationID, ToStationID, TransferReason, TransferDate) 
            VALUES (%s, %s, %s, %s, NOW())
        """, (officer_id, current_station, new_station, transfer_reason))
        
        # Update officer's station
        cursor.execute("""
            UPDATE Officers 
            SET StationID = %s 
            WHERE OfficerID = %s
        """, (new_station, officer_id))
        
        conn.commit()
        flash('Officer transferred successfully', 'success')
        
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        flash(f'Database error: {str(err)}', 'error')
        
    except Exception as e:
        print(f"General Error: {str(e)}")
        flash(f'Error transferring officer: {str(e)}', 'error')
        
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
    
    return redirect(url_for('officers'))

@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)

@app.route('/edit_vehicle/<int:vehicle_id>', methods=['POST'])
def edit_vehicle(vehicle_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Check if image should be deleted
        delete_image = 'delete_image' in request.form
        
        # Get current image path
        cursor.execute("SELECT ImagePath FROM Vehicles WHERE VehicleID = %s", (vehicle_id,))
        result = cursor.fetchone()
        current_image = result['ImagePath'] if result else None
        
        # Handle image update
        image_path = None
        if 'vehicle_image' in request.files and request.files['vehicle_image'].filename:
            file = request.files['vehicle_image']
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename
                
                # Delete old image if it exists
                if current_image:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_image))
                    except:
                        pass
        
        # Update query
        update_query = """
            UPDATE Vehicles 
            SET Type = %s,
                Make = %s,
                Model = %s,
                OwnerName = %s,
                OwnerPhone = %s,
                OwnerAddress = %s,
                UpdatedAt = NOW()
        """
        params = [
            request.form['vehicle_type'],
            request.form['make'],
            request.form['model'],
            request.form['owner_name'],
            request.form['owner_phone'],
            request.form['owner_address']
        ]

        # Handle image path update
        if image_path or delete_image:
            update_query = update_query.replace(
                "UpdatedAt = NOW()",
                "UpdatedAt = NOW(), ImagePath = %s"
            )
            params.append(image_path if image_path else None)
        
        update_query += " WHERE VehicleID = %s"
        params.append(vehicle_id)

        cursor.execute(update_query, tuple(params))
        
        # Delete old image file if requested
        if delete_image and current_image and not image_path:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_image))
            except:
                pass

        db.commit()
        flash('Vehicle details updated successfully')
    except Exception as e:
        db.rollback()
        flash(f'Error updating vehicle: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('violations'))

@app.route('/delete_vehicle/<int:vehicle_id>', methods=['POST'])
def delete_vehicle(vehicle_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        # First check if there are any violations for this vehicle
        cursor.execute("SELECT COUNT(*) FROM TrafficViolations WHERE VehicleID = %s", (vehicle_id,))
        violation_count = cursor.fetchone()[0]
        
        if violation_count > 0:
            flash('Cannot delete vehicle with recorded violations', 'error')
            return redirect(url_for('violations'))
        
        # If no violations, proceed with deletion
        cursor.execute("DELETE FROM Vehicles WHERE VehicleID = %s", (vehicle_id,))
        db.commit()
        flash('Vehicle deleted successfully')
    except Exception as e:
        db.rollback()
        flash(f'Error deleting vehicle: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('violations'))

@app.route('/delete_officer/<int:officer_id>', methods=['POST'])
def delete_officer(officer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Chethan@24',
            database='TrafficManagementSystem'
        )
        cursor = conn.cursor(dictionary=True)

        # First delete transfer records
        cursor.execute("""
            DELETE FROM OfficerTransfers 
            WHERE OfficerID = %s
        """, (officer_id,))

        # Then delete the officer
        cursor.execute("""
            DELETE FROM Officers 
            WHERE OfficerID = %s
        """, (officer_id,))

        if cursor.rowcount > 0:
            conn.commit()
            flash('Officer deleted successfully', 'success')
        else:
            flash('Officer not found', 'error')

    except mysql.connector.Error as e:
        print(f"Database Error: {str(e)}")
        flash(f'Error deleting officer: {str(e)}', 'error')
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
    return redirect(url_for('officers'))

@app.route('/edit_officer/<int:officer_id>', methods=['POST'])
def edit_officer(officer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            UPDATE Officers 
            SET Name = %s,
                OfficerRank = %s,
                StationID = %s,
                Status = %s,
                UpdatedAt = NOW()
            WHERE OfficerID = %s
        """, (
            request.form['name'],
            request.form['rank'],
            request.form['police_station'],
            request.form['status'],
            officer_id
        ))
        
        db.commit()
        flash('Officer details updated successfully')
    except Exception as e:
        db.rollback()
        flash(f'Error updating officer: {str(e)}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('officers'))

@app.route('/delete_station/<int:station_id>', methods=['POST'])
def delete_station(station_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Chethan@24',
            database='TrafficManagementSystem'
        )
        cursor = conn.cursor(dictionary=True)

        # First check if there are any active officers in this station
        cursor.execute("""
            SELECT COUNT(*) as officer_count 
            FROM Officers 
            WHERE StationID = %s AND Status = 'Active'
        """, (station_id,))
        
        result = cursor.fetchone()
        if result and result['officer_count'] > 0:
            flash('Cannot delete station with active officers', 'error')
            return redirect(url_for('stations'))

        # Delete transfer records first
        cursor.execute("""
            DELETE FROM OfficerTransfers 
            WHERE FromStationID = %s OR ToStationID = %s
        """, (station_id, station_id))

        # Delete any officers associated with this station
        cursor.execute("""
            DELETE FROM Officers 
            WHERE StationID = %s
        """, (station_id,))

        # Finally delete the station
        cursor.execute("""
            DELETE FROM PoliceStations 
            WHERE StationID = %s
        """, (station_id,))

        conn.commit()
        flash('Police station deleted successfully', 'success')

    except Exception as e:
        print(f"Error: {str(e)}")
        flash(f'Error deleting police station: {str(e)}', 'error')
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
    return redirect(url_for('stations'))

if __name__ == '__main__':
    create_test_user()  
    app.run(debug=True)
