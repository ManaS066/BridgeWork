from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
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
        return redirect('/login')

    return render_template('company_registration.html')



@app.route('/logincompny', methods=['POST'])
def logincompny():
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
            return render_template("login.html", error="Invalid email or password.")
    else:
        return render_template("login.html", error="Invalid email or password.")
    return redirect(url_for('login'))
@app.route('/add_job', methods=['POST'])
def add_job():
    if 'company_name' not in session:
        return redirect(url_for('login'))

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
from datetime import datetime

@app.route('/company_dashboard', methods=['GET'])
def company_dashboard():
    if 'company_name' not in session:
        return redirect(url_for('login'))

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

    # Format created_at to show only the date (YYYY-MM-DD)
    for project in project_listings:
        if 'created_at' in project and isinstance(project['created_at'], datetime):
            project['created_at'] = project['created_at'].strftime('%Y-%m-%d')

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

    # Send email notification to universities
    send_project_notification(universities, session['company_name'])

    flash('Project added successfully!', 'success')
    return redirect(url_for('company_dashboard'))

def send_project_notification(university_ids, company_name):
    sender_email = "wrkbridge@gmail.com"
    sender_password = "krro rnov pmii obtg"
    login_url = "https://workbridge.com/login"  # Replace with the actual login URL

    # Fetch university details
    universities = universities_collection.find({"_id": {"$in": [ObjectId(uid) for uid in university_ids]}})
    
    for university in universities:
        recipient_email = university['email']
        university_name = university['name']

        subject = "New Project Opportunity on WorkBridge"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Dear <strong>{university_name} Admin</strong>,</p>

            <p>We are pleased to inform you that <strong>{company_name}</strong> has submitted a new project proposal on WorkBridge. Your university has been selected as an eligible participant, and we invite you to review the project details at your earliest convenience.</p>

            <h3>Project Details:</h3>
            <ul>
                <li><strong>Company:</strong> {company_name}</li>
                <li><strong>Project Type:</strong> Industry Collaboration</li>
                <li><strong>Reward:</strong> Competitive Incentives</li>
                <li><strong>Duration:</strong> Flexible</li>
            </ul>

            <p>To access the project details and respond, please log in to your WorkBridge account using the link below:</p>

            <p style="text-align: center; margin: 20px 0;">
                <a href="{login_url}" style="padding: 12px 25px; font-size: 16px; color: #fff; background-color: #007BFF; text-decoration: none; border-radius: 5px;">
                    Review Project on WorkBridge
                </a>
            </p>

            <p>If you have any questions or require further information, feel free to contact our support team.</p>

            <p>We look forward to your university’s participation in this valuable industry-academic collaboration.</p>

            <br>
            <hr>
            <p style="font-size: 14px; text-align: center; color: #666;">
                This is an automated email from WorkBridge. Please do not reply to this email.<br>
                For support, contact us at <a href="mailto:support@workbridge.com">support@workbridge.com</a>.
            </p>
        </body>
        </html>
        """

        # Send email
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))  # Send as HTML email

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            print(f"Email sent successfully to {recipient_email}")

        except Exception as e:
            print(f"Failed to send email to {recipient_email}: {e}")

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
        return redirect(url_for('login'))

    company_name = session.get('company_name', '')
    project_listings_cursor = projects_collection.find({"company_name": company_name})
    project_listings = list(project_listings_cursor)

    return render_template('project_details.html', project_listings=project_listings)

@app.route('/varify_project/<project_id>', methods=['POST'])
def varify_project(project_id):
   
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "completed"}}
    )
    # Check if this prints in logs
    return redirect(url_for('company_dashboard'))
  # ✅ Fix: Redirect to company dashboard

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
        company_obj = companies_collection.find_one({"company_name": name}, {"_id": 0, "company_name": 1})
        if not company_obj:
            flash('Company not found', 'error')
            return redirect(url_for('index'))

        company_name = company_obj['company_name']
        job_listings = list(jobs.find({"company_name": company_name}, {"_id": 0, "job_title": 1, "num_openings": 1, "university_name": 1}))
        project_listings = list(projects_collection.find({"company_name": company_name}))

        total_job_postings = len(job_listings)
        total_applications = sum(int(job.get('num_openings', 0)) for job in job_listings)
        total_universities = len(set(job.get('university_name', '') for job in job_listings if job.get('university_name')))
        
        return render_template('companyProfile.html',
                               company_name=company_name,
                               total_job_postings=total_job_postings,
                               total_applications=total_applications,
                               total_universities=total_universities,
                               job_listings=job_listings,
                               project_listings=project_listings)
    except Exception as e:
        app.logger.error(f"Error in company profile route: {str(e)}")
        flash('An error occurred while fetching company profile', 'error')
        return redirect(url_for('index'))
    
@app.route('/get_selected_students/<job_id>', methods=['GET'])
def get_selected_students(job_id):
    try:
        job = jobs.find_one({"_id": ObjectId(job_id)})
        if job:
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
            return jsonify(student_details)
        return jsonify([]), 404
    except Exception as e:
        print(f"Error fetching selected students: {e}")
        return jsonify([]), 500