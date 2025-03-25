from flask import render_template, request, session, redirect, url_for, jsonify, flash
import requests
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
    university_list = universities_collection.find({})
   
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
                           university_list=university_list,
                           project_listings=project_listings)



@app.route('/add_project', methods=['POST'])
def add_project():
    universities = request.form.getlist('universities[]')
    project_desc = request.form.get('project_desc')
    problem_statement = request.form.get('problem_statement')
    reward = request.form.get('reward')
    duration = request.form.get('duration')

    if not all([universities, project_desc, problem_statement, reward, duration]):
        flash('All fields are required', 'danger')
        return redirect(url_for('company_dashboard'))

    project = {
        'universities': [ObjectId(university) for university in universities],
        'project_desc': project_desc,
        'problem_statement': problem_statement,
        'reward': reward,
        'duration': duration,
        'created_at': datetime.utcnow(),  # Store only the date part
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

@app.route('/complet_project/<project_id>', methods=['POST'])
def complet_project(project_id):
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "completed"}}
    )
    return redirect(url_for('company_dashboard'))



# # Fetch cover photo from Unsplash
# UNSPLASH_ACCESS_KEY = "uirLXmzwo12nm_CP24o-tMQtcZgagCJHMKeFlXfKoYA"
# def get_cover_photo(company_name):
#     url = f"https://api.unsplash.com/search/photos?query={company_name}&client_id={UNSPLASH_ACCESS_KEY}&per_page=1"
#     response = requests.get(url)
#     if response.status_code == 200 and response.json()["results"]:
#         return response.json()["results"][0]["urls"]["regular"]
#     return "https://via.placeholder.com/1200x400?text=No+Image+Found"

@app.route('/company_profile/<name>', methods=['GET'])
def company_profile(name):
    try:
        # Convert the id to ObjectId
        company_obj = companies_collection.find_one({"company_name": name})
        
        # Check if company exists
        if not company_obj:
            flash('Company not found', 'error')
            return redirect(url_for('index'))  # Assume you have an index route
        
        # Extract company name
        company_name = company_obj['company_name']
        
        # Fetch job listings
        job_listings_cursor = jobs.find({"company_name": company_name})
        job_listings = list(job_listings_cursor)
        
        # Calculate job-related statistics
        total_job_postings = len(job_listings)
        total_applications = sum([
            int(job.get('num_openings', 0)) for job in job_listings
        ])
        
        # Get unique universities
        total_universities = len(set([
            job.get('university_name', '') 
            for job in job_listings 
            if job.get('university_name')
        ]))
        
        # Fetch project listings
        project_listings_cursor = projects_collection.find({"company_name": company_name})
        project_listings = list(project_listings_cursor)
        
        return render_template('companyProfile.html',
                               company_name=company_name,
                               total_job_postings=total_job_postings,
                               total_applications=total_applications,
                               total_universities=total_universities,
                               job_listings=job_listings,
                               project_listings=project_listings)
    
    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Error in company profile route: {str(e)}")
        
        # Flash a user-friendly error message
        flash('An error occurred while fetching company profile', 'error')
        
        # Redirect to a safe page
        return redirect(url_for('index'))  # Assume you have an index route
