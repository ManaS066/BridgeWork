from flask import render_template, request, session, redirect, url_for, jsonify, flash
from app import app, companies_collection, jobs, universities_collection, students_collection, pending_companies_collection, projects_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone, timedelta

@app.route('/register_company', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        company_name = request.form['company_name']
        employee_size = request.form['employee_size']
        email = request.form['email']
        password = request.form['password']

        # Check if the company already exists
        existing_company = companies_collection.find_one({"email": email})
        if existing_company:
            flash("Company with this email already exists", "danger")
            return redirect(url_for('company_registration'))

        # Insert new company registration request with a timestamp
        pending_companies_collection.insert_one({
            "company_name": company_name,
            "email": email,
            "password": password,
            "employee_size": employee_size,
            "status": "pending",
            "created_at": datetime.now(timezone.utc)
        })

        flash("Company registration request submitted successfully!", "success")
        return redirect('/login_company')

    return render_template('company_registration.html')

@app.route('/login_company', methods=['GET'])
def company_login_page():
    return render_template('company_login.html')

@app.route('/login_company', methods=['POST'])
def login_company():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    company = companies_collection.find_one({"email": email})

    if company:
        if company['password'] == password:
            session['company_id'] = str(company['_id'])
            session['company_name'] = company['company_name']
            return redirect(url_for('company_dashboard', company_name=company['company_name']))
        else:
            return render_template("company_login.html", error="Invalid email or password.")
    else:
        return render_template("company_login.html", error="Invalid email or password.")

@app.route('/add_job', methods=['POST'])
def add_job():
    if 'company_name' not in session:
        return redirect(url_for('login_company'))

    university_id = request.form.get('university')
    departments = request.form.getlist('departments')
    job_title = request.form.get('job_title')
    job_desc = request.form.get('job_desc')
    num_openings = request.form.get('num_openings')
    job_mode = request.form.get('job_mode')

    if not all([university_id, departments, job_title, job_desc, num_openings, job_mode]):
        return jsonify({"message": "All fields are required"}), 400

    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    job_id = jobs.insert_one({
        "university_name": university_name,
        "departments": departments,
        "job_title": job_title,
        "job_desc": job_desc,
        "num_openings": num_openings,
        "job_mode": job_mode,
        "company_name": session['company_name'],
        "flag": 0
    }).inserted_id

    return redirect(url_for("company_dashboard"))

@app.route('/company_dashboard', methods=['GET'])
def company_dashboard():
    if 'company_name' not in session:
        return redirect(url_for('company_login'))

    company_name = session.get('company_name', '')
    job_listings_cursor = jobs.find({"company_name": company_name})
    job_listings = list(job_listings_cursor)
    total_job_postings = len(job_listings)
    total_applications = sum([int(job.get('num_openings', 0)) for job in job_listings])
    pending_applications = sum([int(job.get('num_applications', 0)) for job in job_listings if job.get('flag') == 0])
    accepted_applications = sum([int(job.get('num_applications', 0)) for job in job_listings if job.get('flag') == 3])
    total_universities = len(set([job.get('university_name') for job in job_listings]))

    job_titles = [job['job_title'] for job in job_listings]
    job_applications = [int(job.get('num_applications', 0)) for job in job_listings]
    application_status = [
        sum([int(job.get('num_applications', 0)) for job in job_listings if job.get('flag') == 0]),
        sum([int(job.get('num_applications', 0)) for job in job_listings if job.get('flag') == 3]),
        sum([int(job.get('num_applications', 0)) for job in job_listings if job.get('flag') == 2])
    ]
    project_listings_cursor = projects_collection.find({"company_name": company_name})
    project_listings = list(project_listings_cursor)

   
    return render_template('company_dashboard.html', 
                           company_name=company_name, 
                           job_listings=job_listings, 
                           total_job_postings=total_job_postings,
                           total_applications=total_applications,
                           pending_applications=pending_applications,
                           accepted_applications=accepted_applications,
                           total_universities=total_universities,
                           job_titles=job_titles,
                           job_applications=job_applications,
                           application_status=application_status,
                          
                           project_listings=project_listings)

@app.route('/get_selected_students/<job_id>', methods=['GET'])
def get_selected_students(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        return jsonify([])

    selected_students = job.get('selected_students', [])
    student_details = []
    for student_id in selected_students:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if student:
            student_details.append({
                "_id": str(student['_id']),
                "name": student.get('name', ''),
                "email": student.get('email', ''),
                "course": student.get('course', ''),
                "gpa": student.get('gpa', '')
            })

    return jsonify(student_details)

@app.route('/add_project', methods=['POST'])
def add_project():
    university1 = request.form.get('university1')
    university2 = request.form.get('university2')
    university3 = request.form.get('university3')
    project_desc = request.form.get('project_desc')
    problem_statement = request.form.get('problem_statement')
    reward = request.form.get('reward')
    duration = request.form.get('duration')

    if not all([university1, project_desc, problem_statement, reward, duration]):
        flash('All fields are required', 'danger')
        return redirect(url_for('company_dashboard'))

    project = {
        'university1': university1,
        'university2': university2,
        'university3': university3,
        'count':0,
        'project_desc': project_desc,
        'problem_statement': problem_statement,
        'reward': reward,
        'duration': duration,
        'created_at': datetime.utcnow(),
        'assigned_to': None,
        'status': 'not_assigned',
        'company_name': session['company_name']
    }

    project_id = projects_collection.insert_one(project).inserted_id

    # Schedule a task to update the project status to "rejected" after 3 days if not assigned
    app.apscheduler.add_job(
        func=reject_unassigned_project,
        trigger='date',
        run_date=datetime.utcnow() + timedelta(days=3),
        args=[project_id],
        id=str(project_id)
    )

    flash('Project added successfully!', 'success')
    return redirect(url_for('company_dashboard'))

def reject_unassigned_project(project_id):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if project and project['status'] == 'not_assigned':
        projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"status": "rejected"}}
        )

@app.route('/project_details', methods=['GET'])
def project_details():
    if 'company_name' not in session:
        return redirect(url_for('company_login'))

    company_name = session.get('company_name', '')
    project_listings_cursor = projects_collection.find({"company_name": company_name})
    project_listings = list(project_listings_cursor)

    return render_template('project_details.html', project_listings=project_listings)
