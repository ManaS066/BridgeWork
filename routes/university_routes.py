import bson
from flask import render_template, request, session, redirect, url_for, jsonify, flash
from app import app, universities_collection, jobs, students_collection, pending_universities_collection, projects_collection
from bson.objectid import ObjectId
from datetime import datetime, timedelta

@app.route('/get_universities', methods=['GET'])
def get_universities():
    universities = universities_collection.find({})
    return jsonify([{"id": str(u["_id"]), "name": u["name"], "email": u["email"], "address": u["address"]} for u in universities])

@app.route('/get_departments/<university_id>', methods=['GET'])
def get_departments(university_id):
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    return jsonify(university.get("departments", [])) if university else jsonify([])

@app.route('/login_university', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        university = universities_collection.find_one({"email": email, "password": password})
        
        if university:
            session['university_id'] = str(university['_id'])
            session['university_name'] = university['name']
            
            if not university.get('info_completed'):
                return redirect(url_for('university_info'))
            
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

        # Insert new university registration request
        pending_universities_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "departments": departments,
            "status": "pending"
        })

        flash("University registration request submitted successfully!", "success")
        return redirect(url_for('university_login'))

    return render_template('uniReg.html')

@app.route('/university_dashboard', methods=['GET'])
def university_dashboard():
    university_id = session.get('university_id', '')
    university_name = session.get('university_name', '')
    if not university_id or not university_name:
        return jsonify({"message": "University ID and name are required"}), 400

    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    if not university:
        return jsonify({"message": "University not found"}), 404

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
        job['count'] = job.get('count', 0)  # Ensure 'count' is included
        
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

    # Fetch all students associated with the university
    students = list(students_collection.find({"university_name": university_name}))
    for student in students:
        student['_id'] = str(student['_id'])
        student['name'] = student.get('name', '')
        student['email'] = student.get('email', '')
        student['course'] = student.get('course', '')
        student['gpa'] = student.get('gpa', '')
        student['rollno'] = student.get('rollno', '')
       
    student_count = len(students)
    job_count = len(job_listings)

    # Fetch the number of projects for the university
    project_count = projects_collection.count_documents({"assigned_to_id": ObjectId(university_id)})

    # Fetch all projects assigned to the university
    current_projects = list(projects_collection.find({"assigned_to_id": ObjectId(university_id), "status": "assigned"}))
    pending_review_projects = list(projects_collection.find({"assigned_to_id": ObjectId(university_id), "status": "done"}))
    completed_projects = list(projects_collection.find({"assigned_to_id": ObjectId(university_id), "status": "completed"}))

    # Convert ObjectId to string for JSON serialization
    university['_id'] = str(university['_id'])

    return render_template('university_dashboard.html', university=university, job_listings=job_listings, students=students, student_count=student_count, job_count=job_count, project_count=project_count, current_projects=current_projects, pending_review_projects=pending_review_projects, completed_projects=completed_projects)

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
                "gpa": student.get('gpa', '')
            })

    # Update the flag to 3
    jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"flag": 3}})

    # Logic to send the selected students' details to the company
    # ...

    flash("Students' details sent to the company successfully!", "success")
    return redirect(url_for('university_dashboard'))

@app.route('/accept_project/<project_id>', methods=['POST'])
def accept_project(project_id):
    university_name = session.get('university_name', '')
    university_id = session.get('university_id', '')
    if not university_name:
        flash("University name is required", "danger")
        return redirect(url_for('university_dashboard'))

    project = projects_collection.find_one({"_id": ObjectId(project_id)})

    if project:
        projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {"status": "assigned", "assigned_to": university_name, "assigned_to_id":ObjectId(university_id)}})
        flash("Project accepted successfully!", "success")
    else:
        flash("Project not found!", "danger")

    return redirect(url_for('university_dashboard'))

@app.route('/reject_project/<project_id>', methods=['POST'])
def reject_project(project_id):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})

    if project:
        projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {"status": "rejected"}})
        flash("Project rejected successfully!", "success")
    else:
        flash("Project not found!", "danger")

    return redirect(url_for('university_dashboard'))

@app.route('/university_info', methods=['GET', 'POST'])
def university_info():
    if request.method == 'POST':
        university_id = session.get('university_id')
        if not university_id:
            flash("You need to log in first.", "danger")
            return redirect(url_for('university_login'))

        address = request.form['address']
        first_year = request.form['first_year']
        second_year = request.form['second_year']
        third_year = request.form['third_year']
        fourth_year = request.form['fourth_year']
        contact_person = request.form['contact_person']
        contact_email = request.form['contact_email']
        contact_phone = request.form['contact_phone']

        universities_collection.update_one(
            {"_id": ObjectId(university_id)},
            {"$set": {
                "address": address,
                "first_year": first_year,
                "second_year": second_year,
                "third_year": third_year,
                "fourth_year": fourth_year,
                "contact_person": contact_person,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "info_completed": True
            }}
        )

        flash("Information saved successfully.", "success")
        return redirect(url_for('university_dashboard'))

    return render_template('university_info.html')

@app.route('/get_project_requests', methods=['GET'])
def get_project_requests():
    university_id = session.get('university_id')
    university_name = session.get('university_name')
    if not university_id:
        return jsonify({"message": "University ID is required"}), 400

    # Debug print to check university ID
    

    # Query the projects collection to find projects for the university
    project_requests = list(projects_collection.find({
        "$or": [
            {"university1": (university_id)},
            {"university2": (university_id)},
            {"university3": (university_id)}
        ],
        "status": "not_assigned"
    }))

    # Debug print to check fetched project requests
   

    # Convert ObjectId to string for each project
    for project in project_requests:
        project['_id'] = str(project['_id'])

    # Return the project requests as JSON
    return jsonify(project_requests)

@app.route('/get_job_history', methods=['GET'])
def get_job_history():
    university_id = session.get('university_id', '')
    if not university_id:
        return jsonify({"message": "University ID is required"}), 400

    job_history = list(jobs_collection.find({"university_id": ObjectId(university_id), "status": "completed"}))
    for job in job_history:
        job['_id'] = str(job['_id'])
    return jsonify(job_history)

@app.route('/get_project_history', methods=['GET'])
def get_project_history():
    university_id = session.get('university_id', '')
    if not university_id:
        return jsonify({"message": "University ID is required"}), 400

    completed_projects = list(projects_collection.find({"assigned_to_id": ObjectId(university_id), "status": "completed"}))
    for project in completed_projects:
        project['_id'] = str(project['_id'])
        project['assigned_to_id'] = str(project['assigned_to_id'])
    return jsonify(completed_projects)

@app.route('/university_profile/<university_id>', methods=['GET'])
def university_profile(university_id):
    try:
        university = universities_collection.find_one({"_id": ObjectId(university_id)})
    except bson.errors.InvalidId:
        return "Invalid University ID", 400

    if not university:
        return "University not found", 404

    # Fetch the number of projects for the university
    project_count = projects_collection.count_documents({"assigned_to_id": ObjectId(university_id)})

    # Fetch the number of jobs assigned to the university
    job_count = jobs.count_documents({"university_name": university['name']})

    # Convert ObjectId to string for JSON serialization
    university['_id'] = str(university['_id'])

    return render_template('universityProfile.html', university=university, project_count=project_count, job_count=job_count)

@app.route("/done_project/<project_id>",methods=['POST'])
def done_project(project_id):
    
    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if project:
        projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {"status": "done"}})
        flash("Project completed successfully!", "success")
    else:
        flash("Project not found!", "danger")
    return redirect(url_for('university_dashboard'))

@app.route('/complete_project/<project_id>', methods=['POST'])
def complete_project(project_id):
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "done"}}
    )
    return redirect(url_for('university_dashboard'))

@app.route('/confirm_project/<project_id>', methods=['POST'])
def confirm_project(project_id):
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "completed"}}
    )
    return redirect(url_for('university_dashboard'))

@app.route('/project_history', methods=['GET'])
def project_history():
    university_id = session.get('university_id', '')
    if not university_id:
        flash("University ID is required", "danger")
        return redirect(url_for('university_dashboard'))

    completed_projects = list(projects_collection.find({"assigned_to_id": ObjectId(university_id), "status": "completed"}))
    for project in completed_projects:
        project['_id'] = str(project['_id'])
        project['assigned_to_id'] = str(project['assigned_to_id'])

    return render_template('project_history.html', completed_projects=completed_projects)

@app.route('/get_selected_students', methods=['GET'])
def get_selected_students():
    job_id = request.args.get('job_id')
    job = jobs.find_one({"_id": ObjectId(job_id)})

    if not job:
        return jsonify([])

    selected_students = job.get('selected_students', [])
    student_details = []

    for student_id in selected_students:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if student:
            student_details.append({
                "name": student.get('name', ''),
                "email": student.get('email', ''),
                "course": student.get('course', ''),
                "gpa": student.get('gpa', '')
            })

    return jsonify(student_details)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')