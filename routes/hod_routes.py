import smtplib
from flask import render_template, request, session, redirect, url_for, flash, jsonify
from app import app, hod_collection, jobs, universities_collection, students_collection,projects_collection
from bson.objectid import ObjectId
mail = "wrkbridge@gmail.com"
code = "krro rnov pmii obtg"
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@app.route('/hod_register', methods=['GET'])
def hod_register_page():
    return render_template('hod_register.html')

@app.route('/register_hod', methods=['POST'])
def register_hod():
    data = request.json
    university_id = data.get('universityId')
    department = data.get('department')
    name = data.get('name')
    contact = data.get('contact')
    employee_code = data.get('employeeCode')
    email = data.get('email')
    password = data.get('password')

    if not all([university_id, department, name, contact, employee_code, email, password]):
        return jsonify({"message": "All fields are required"}), 400

    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    if not university:
        return jsonify({"message": "University not found"}), 404

    # Assuming the correct field name is 'name'
    university_name = university.get('name') or university.get('university_name')
    if not university_name:
        return jsonify({"message": "University name not found"}), 404

    hod = {
        "university_name": university_name,
        "department": department,
        "name": name,
        "contact": contact,
        "employee_code": employee_code,
        "email": email,
        "password": password,  # Note: In a real application, ensure to hash the password before storing it
        "approved": False  # Mark as pending approval
    }

    hod_collection.insert_one(hod)
    return jsonify({"message": "HOD registration request submitted successfully"}), 201

@app.route('/hod_login', methods=['GET'])
def hod_login_page():
    return render_template('hod_login.html')

@app.route('/hod_login', methods=['POST'])
def hod_login():
    email = request.form['email']
    password = request.form['password']

    hod = hod_collection.find_one({"email": email, "password": password})
    
    if hod:
        if not hod.get('approved', False):
            flash("Your registration is pending approval.", "warning")
            return redirect(url_for('hod_login'))
        elif hod.get('approved') == False:
            flash("Your registration has been rejected.", "danger")
            return redirect(url_for('hod_login'))

        session['hod_id'] = str(hod['_id'])
        session['hod_email'] = email
        session['university_name'] = hod['university_name']
        session['department'] = hod['department']
        return redirect(url_for('hod_dashboard'))
    else:
        flash("Invalid email or password", "danger")
        return redirect(url_for('hod_login'))

@app.route('/hod_dashboard', methods=['GET'])
def hod_dashboard():
    hod_id = session.get('hod_id', '')
    university_name = session.get('university_name', '')
    department = session.get('department', '')

    if not university_name or not department:
         return redirect(url_for('hod_login'))


    # Fetch job listings for the department
    job_listings = list(jobs.find({
        "university_name": university_name,
        "departments": department,
        "flag": 1
    }))
    for job in job_listings:
        job['_id'] = str(job['_id'])

    # Fetch assigned projects
    assigned_projects = list(projects_collection.find({"assigned_hods": ObjectId(hod_id)}))
    for project in assigned_projects:
        project['_id'] = str(project['_id'])

    # Fetch pending student registrations
    pending_registrations = list(students_collection.find({
        "university_name": university_name,
        "department": department,
        "approved": False
    }))
    for registration in pending_registrations:
        registration['_id'] = str(registration['_id'])

    # Fetch students in the department
    students = list(students_collection.find({"department": department}))

    return render_template('hod_dashboard.html', 
        university_name=university_name, 
        department=department, 
        job_listings=job_listings, 
        students=students,
        assigned_projects=assigned_projects,
        pending_registrations=pending_registrations
    )

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


@app.route('/assign_students_to_project', methods=['POST'])
def assign_students_to_project():
    project_id = request.form['project_id']
    student_ids = request.form.getlist('students')

    project = projects_collection.find_one({"_id": ObjectId(project_id)})

    if not project:
        flash("Project not found", "danger")
        return redirect(url_for('hod_dashboard'))

    # Update the project with the assigned students
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"assigned_students": [ObjectId(student_id) for student_id in student_ids]}}
    )

    # Fetch selected students' emails
    selected_students = students_collection.find({"_id": {"$in": [ObjectId(sid) for sid in student_ids]}})

    for student in selected_students:
        student_email = student["email"]
        student_name = student["name"]

        subject = "Congratulations! You Have Been Selected for a Project"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Dear <strong>{student_name}</strong>,</p>

            <p>We are pleased to inform you that you have been selected for the project: <strong>{project['project_desc']}</strong> on WorkBridge.</p>

            <h3>Project Details:</h3>
            <ul>
                <li><strong>Company:</strong> {project['company_name']}</li>
               
                <li><strong>Deadline:</strong> {project['duration']}</li>
            </ul>

            <p>To get started, please log in to your WorkBridge account:</p>

            <p style="text-align: center; margin: 20px 0;">
                <a href="https://workbridge.com/login" style="padding: 12px 25px; font-size: 16px; color: #fff; background-color: #007BFF; text-decoration: none; border-radius: 5px;">
                    Access Your Project
                </a>
            </p>

            <p>We look forward to your participation and wish you success in this project!</p>

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
        send_email(student_email, subject, body)

    flash("Students assigned to project successfully! Emails have been sent.", "success")
    return redirect(url_for('hod_dashboard'))

@app.route('/approve_registration', methods=['POST'])
def approve_registration():
    hod_id = session.get('hod_id', '')
    if not hod_id:
        return jsonify({"message": "Unauthorized"}), 401

    registration_id = request.form.get('registration_id')
    action = request.form.get('action')  # 'approve' or 'reject'
    rejection_reason = request.form.get('reason', 'Not specified')  # Optional reason

    if not registration_id or not action:
        return jsonify({"message": "Invalid request"}), 400

    try:
        registration = students_collection.find_one({"_id": ObjectId(registration_id)})
        
        if not registration:
            return jsonify({"message": "Registration not found"}), 404

        student_mail = registration['email']

        if action == 'approve':
            # Update registration status to approved
            students_collection.update_one(
                {"_id": ObjectId(registration_id)},
                {"$set": {"approved": True, "status": "approved"}}
            )

            subject = "🎉 Your WorkBridge Account Has Been Approved!"
            email_body = f"""
Dear {registration['name']},

🎉 Congratulations! Your account has been approved by your HOD. You can now log in to WorkBridge and explore exciting opportunities.

📌 University: {registration['university_name']}
📌 Department: {registration['department']}
📌 Roll No: {registration['rollno']}

🔗 Login to WorkBridge: https://workbridge.com/login

Start your journey today and make the most of these opportunities!

Best Regards,  
WorkBridge Team
"""

            send_email(student_mail, subject, email_body)

        elif action == 'reject':
            # Delete the registration record
            students_collection.delete_one({"_id": ObjectId(registration_id)})

            subject = "⚠️ Your WorkBridge Registration Has Been Rejected"
            email_body = f"""
Dear {registration['name']},

We regret to inform you that your registration for WorkBridge has been rejected by the HOD.

📌 University: {registration['university_name']}
📌 Department: {registration['department']}
📌 Roll No: {registration['rollno']}

❌ **Reason for Rejection:** {rejection_reason}

If you believe this is an error or would like to apply again, please contact your HOD.

Best Regards,  
WorkBridge Team
"""

            send_email(student_mail, subject, email_body)

        return redirect(url_for('hod_dashboard'))

    except Exception as e:
        return jsonify({"message": str(e)}), 500

def send_email(to_email, subject, body):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = mail
        sender_password = code

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        # Attach the email body as HTML
        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        
        print(f"Email sent successfully to {to_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")
