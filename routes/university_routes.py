from flask import render_template, request, session, redirect, url_for, jsonify, flash
from app import app, universities_collection, jobs, students_collection
from bson.objectid import ObjectId

@app.route('/get_universities', methods=['GET'])
def get_universities():
    universities = universities_collection.find({}, {"_id": 1, "name": 1})
    return jsonify([{"id": str(u["_id"]), "name": u["name"]} for u in universities])

@app.route('/get_departments/<university_id>', methods=['GET'])
def get_departments(university_id):
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    return jsonify(university.get("departments", [])) if university else jsonify([])

@app.route('/university_login', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        university = universities_collection.find_one({"email": email, "password": password})
        
        if university:
            session['university_name'] = university['name']
            return redirect(url_for('university_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('university_login'))

    return render_template('university_login.html')

@app.route('/university_register', methods=['GET', 'POST'])
def university_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        departments = request.form.getlist('departments')

        # Check if the university already exists
        existing_university = universities_collection.find_one({"email": email})
        if existing_university:
            flash("University with this email already exists", "danger")
            return redirect(url_for('university_register'))

        # Insert new university
        universities_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "departments": departments
        })

        flash("University registered successfully!", "success")
        return redirect(url_for('university_login'))

    return render_template('uniReg.html')

@app.route('/university_dashboard', methods=['GET'])
def university_dashboard():
    university_name = session.get('university_name', '')

    if not university_name:
        return jsonify({"message": "University name is required"}), 400

    job_listings = list(jobs.find({"university_name": university_name}))

    for job in job_listings:
        job['_id'] = str(job['_id'])
        job['departments'] = job.get('departments', [])
        job['job_title'] = job.get('job_title', '')
        job['job_desc'] = job.get('job_desc', '')
        job['num_openings'] = job.get('num_openings', '')
        job['job_mode'] = job.get('job_mode', '')
        job['company_name'] = job.get('company_name', '')
        job['flag'] = job.get('flag', 0)
        
        # Fetch student details
        selected_students = job.get('selected_students', [])
        student_details = []
        for student_id in selected_students:
            student = students_collection.find_one({"_id": ObjectId(student_id)})
            if student:
                student_details.append({
                    "name": student.get('name', ''),
                    "email": student.get('email', ''),
                    "course": student.get('course', ''),
                    "cgpa": student.get('gpa', '')
                })
        job['selected_students'] = student_details
    
    return render_template('university_dashboard.html', university_name=university_name, job_listings=job_listings)

@app.route('/approve_job/<job_id>', methods=['POST'])
def approve_job(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id)})

    if job:
        jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"flag": 1}})
        flash("Job approved successfully!", "success")
    else:
        flash("Job not found!", "danger")
    
    university_name = job.get('university_name', '')
    return redirect(url_for('university_dashboard', university_name=university_name))

@app.route('/send_students_to_company', methods=['POST'])
def send_students_to_company():
    job_id = request.form['job_id']
    job = jobs.find_one({"_id": ObjectId(job_id)})

    if not job:
        flash("Job not found", "danger")
        return redirect(url_for('university_dashboard'))

    selected_students = job.get('selected_students', [])
    student_details = []

    for student_id in selected_students:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if student:
            student_details.append({
                "name": student.get('name', ''),
                "email": student.get('email', ''),
                "course": student.get('course', ''),
                "cgpa": student.get('cgpa', '')
            })

    # Logic to send the selected students' details to the company
    # ...

    flash("Students' details sent to the company successfully!", "success")
    return redirect(url_for('university_dashboard'))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')