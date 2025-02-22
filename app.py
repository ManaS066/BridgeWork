from flask import Flask, flash, redirect, render_template, request, jsonify, session, url_for
from flask_pymongo import PyMongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://manasranjanpradhan2004:pRZ0F9oyRoY1FHxs@university.m80kj.mongodb.net/University?retryWrites=true&w=majority"
app.config["MONGO_URI"] = MONGO_URI

mongo = PyMongo(app)
app.secret_key = os.urandom(24)
# References to collections
db = mongo.db
universities_collection = db.universities
hod_collection = db.hods
students_collection = db.students
companies_collection = db.companies
jobs = db.jobs

@app.route('/hod_register', methods=['GET'])
def hod_register_page():
    return render_template('hod_register.html')

@app.route('/get_universities', methods=['GET'])
def get_universities():
    universities = universities_collection.find({}, {"_id": 1, "name": 1})
    return jsonify([{"id": str(u["_id"]), "name": u["name"]} for u in universities])

@app.route('/get_departments/<university_id>', methods=['GET'])
def get_departments(university_id):
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    return jsonify(university.get("departments", [])) if university else jsonify([])

@app.route('/register_hod', methods=['POST'])
def register_hod():
    data = request.json
    university_id = data.get('universityId')
    department = data.get('department')
    email = data.get('email')
    password = data.get('password')

    if not all([university_id, department, email, password]):
        return jsonify({"message": "All fields are required"}), 400

    # Fetch university name from the database
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    # Insert HOD with university name
    hod_id = hod_collection.insert_one({
        "university_name": university_name,  # Store university name instead of ID    # Store university ID for reference
        "department": department,
        "email": email,
        "password": password
    }).inserted_id

    return jsonify({
        "message": "HOD registered successfully!",
        "hod_id": str(hod_id)
    })


@app.route('/student_register', methods=['GET'])
def student_register_page():
    return render_template('student_register.html')

@app.route('/register_student', methods=['POST'])
def register_student():
    university_id = request.form.get('universityId')
    department = request.form.get('department')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    rollno = request.form.get('roll_number')
    registration_no = request.form.get('reg_number')

    if not all([university_id, department, name, email, password, rollno, registration_no]):
        return jsonify({"message": "All fields are required"}), 400

    # Fetch university name from the database
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    # Insert student with university name
    student_id = students_collection.insert_one({
        "university_name": university_name,  # Store name instead of ID
        "department": department,
        "name": name,
        "email": email,
        "password": password,
        "rollno": rollno,
        "registration_no": registration_no
    }).inserted_id

    return render_template('student_login.html', message="Student registered successfully!")

@app.route('/register_company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'GET':
        return render_template('company_registration.html')

    data = request.form
    company_name = data.get('company_name')
    employee_size = data.get('employee_size')
    email = data.get('email')
    password = data.get('password')

    if not all([company_name, employee_size, email, password]):
        return jsonify({"message": "All fields are required"}), 400

    company_id = companies_collection.insert_one({
        "company_name": company_name,
        "employee_size": employee_size,
        "email": email,
        "password": password
    }).inserted_id

    return jsonify({
        "message": "Company registered successfully!",
        "company_id": str(company_id)
    })

@app.route('/login_company', methods=['GET'])
def company_login_page():
    return render_template('company_login.html')

@app.route('/login_company', methods=['POST'])
def login_company():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    company = companies_collection.find_one({"email": email, "password": password})

    if company: 
        print("Access")
        return redirect(url_for('company_dashboard', company_name=company['company_name']))
    else:
        return render_template("company_login.html", error="Invalid email or password.")

@app.route('/add_job', methods=['POST'])
def add_job():
    # Extract job details from the form
    university_id = request.form.get('university')
    departments = request.form.getlist('departments')  # List of selected departments
    job_title = request.form.get('job_title')
    job_desc = request.form.get('job_desc')

    if not all([university_id, departments, job_title, job_desc]):
        return jsonify({"message": "All fields are required"}), 400

    # Fetch university name from the database
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    # Insert job posting with university name
    job_id = db.jobs.insert_one({
        "university_name": university_name,  # Store name instead of ID
        "departments": departments,
        "job_title": job_title,
        "job_desc": job_desc,
        "company_name": "Accenture",  # Add a comma here
        "flag": 0
    }).inserted_id

    return redirect(url_for("company_dashboard"))

# Add job posting route to handle the form submission
@app.route('/company_dashboard', methods=['GET'])
def company_dashboard():
    # You can fetch job listings for this company to show on the dashboard
    company_name = request.args.get('company_name', '')
    jobs = db.jobs.find()
    job_listings = [{"job_title": job["job_title"], "job_desc": job["job_desc"]} for job in jobs]

    return render_template('company_dashboard.html', company_name=company_name, job_listings=job_listings)

@app.route('/university_login', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find university in DB
        university = universities_collection.find_one({"email": email,"password":password})
        
        if university :
            session['university_name'] = university['name']
            return redirect(url_for('university_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('university_login'))

    return render_template('university_login.html')

from bson import ObjectId

@app.route('/university_dashboard', methods=['GET'])
def university_dashboard():
    university_name = "giet"  # Replace with session or dynamic value as needed

    if not university_name:
        return jsonify({"message": "University name is required"}), 400

    # Fetch jobs that belong to this university and have flag set to 0
    job_listings = list(jobs.find({"university_name": university_name}))

    # Convert ObjectId to string
    for job in job_listings:
        job['_id'] = str(job['_id'])
    
    return render_template('university_dashboard.html', university_name=university_name, job_listings=job_listings)

@app.route('/approve_job/<job_id>', methods=['POST'])
def approve_job(job_id):
    # Find the job by its ID
    job = jobs.find_one({"_id": ObjectId(job_id)})

    if job:
        # Update the flag value of the job to 1 (approved)
        jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"flag": 1}})
        flash("Job approved successfully!", "success")
    else:
        flash("Job not found!", "danger")
    
    # Redirect back to the university_dashboard with university_name
    university_name = job.get('university_name', '')
    return redirect(url_for('university_dashboard', university_name=university_name))

@app.route('/hod_login', methods=['GET'])
def hod_logn():
    return render_template('hod_login.html')


@app.route('/hod_login', methods=['POST'])
def hod_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find HOD in the database using email and password
        hod = hod_collection.find_one({"email": email, "password": password})
        
        if hod:
            session['hod_email'] = email
            session['university_name'] = hod['university_name']  # Changed to university_name
            session['department'] = hod['department']
            return redirect(url_for('hod_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('hod_login'))

    return render_template('hod_login.html')
    
@app.route('/hod_dashboard', methods=['GET'])
def hod_dashboard():
    # Get university and department from session
    university_name = session.get('university_name', '')
    department = session.get('department', '')

    if not university_name or not department:
        return jsonify({"message": "University name and department are required"}), 400

    # Fetch approved jobs that belong to the university and department
    job_listings = list(jobs.find({
        "university_name": university_name,
        "departments": department,
        "flag": 1  # Only approved jobs (flag == 1)
    }))

    # Convert ObjectId to string for all job listings
    for job in job_listings:
        job['_id'] = str(job['_id'])

    # Render the HOD dashboard template with job listings
    return render_template('hod_dashboard.html', university_name=university_name, department=department, job_listings=job_listings)


@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        student = students_collection.find_one({"email": email, "password": password})

        if student:
            session['student_id'] = str(student['_id'])
            session['student_name'] = student['name']
            return redirect(url_for('student_dashboard'))  # Redirect to student dashboard
        else:
            return render_template('student_login.html', error="Invalid Email or Password")

    return render_template('student_login.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    # Fetch student details from MongoDB
    student = students_collection.find_one({"_id": ObjectId(session['student_id'])})

    if not student:
        return redirect(url_for('student_login'))

    return render_template('student_dashboard.html', student=student)


@app.route('/logout', methods=['GET'])
def logout():
    # Logout functionality here
    return redirect(url_for('login_company'))

if __name__ == '__main__':
    app.run(debug=True)
