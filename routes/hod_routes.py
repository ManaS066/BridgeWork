from flask import render_template, request, session, redirect, url_for, flash, jsonify
from app import app, hod_collection, jobs, universities_collection, students_collection
from bson.objectid import ObjectId

@app.route('/hod_register', methods=['GET'])
def hod_register_page():
    return render_template('hod_register.html')

@app.route('/register_hod', methods=['POST'])
def register_hod():
    data = request.json
    university_id = data.get('universityId')
    department = data.get('department')
    email = data.get('email')
    password = data.get('password')

    if not all([university_id, department, email, password]):
        return jsonify({"message": "All fields are required"}), 400

    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    # Check if the HOD already exists
    existing_hod = hod_collection.find_one({"email": email})
    if existing_hod:
        return jsonify({"message": "HOD with this email already exists"}), 400

    hod_id = hod_collection.insert_one({
        "university_name": university_name,
        "department": department,
        "email": email,
        "password": password
    }).inserted_id

    return jsonify({
        "message": "HOD registered successfully!",
        "hod_id": str(hod_id)
    })

@app.route('/hod_login', methods=['GET'])
def hod_login_page():
    return render_template('hod_login.html')

@app.route('/hod_login', methods=['POST'])
def hod_login():
    email = request.form['email']
    password = request.form['password']

    hod = hod_collection.find_one({"email": email, "password": password})
    
    if hod:
        session['hod_email'] = email
        session['university_name'] = hod['university_name']
        session['department'] = hod['department']
        return redirect(url_for('hod_dashboard'))
    else:
        flash("Invalid email or password", "danger")
        return redirect(url_for('hod_login'))

@app.route('/hod_dashboard', methods=['GET'])
def hod_dashboard():
    university_name = session.get('university_name', '')
    department = session.get('department', '')

    if not university_name or not department:
        return jsonify({"message": "University name and department are required"}), 400

    job_listings = list(jobs.find({
        "university_name": university_name,
        "departments": department,
        "flag": 1
    }))

    for job in job_listings:
        job['_id'] = str(job['_id'])

    students = list(students_collection.find({"department": department}))

    return render_template('hod_dashboard.html', university_name=university_name, department=department, job_listings=job_listings, students=students)

@app.route('/submit_students', methods=['POST'])
def submit_students():
    job_id = request.form['job_id']
    selected_students = request.form.getlist('students')
    
    job = jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        flash("Job not found", "danger")
        return redirect(url_for('hod_dashboard'))

    jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"flag": 2, "selected_students": selected_students}}
    )

    flash("Students submitted successfully!", "success")
    return redirect(url_for('hod_dashboard'))