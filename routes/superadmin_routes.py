from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from app import app, companies_collection, universities_collection, students_collection, super_admins_collection, pending_universities_collection, pending_companies_collection, projects_collection, jobs
from bson.objectid import ObjectId
from datetime import datetime

@app.route('/super_admin_login', methods=['GET', 'POST'])
def super_admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        super_admin = super_admins_collection.find_one({"email": email, "password": password})
        
        if super_admin:
            session['user_id'] = str(super_admin['_id'])
            session['user_role'] = 'super_admin'
            session['user_name'] = super_admin['name']
            return redirect(url_for('super_admin_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('super_admin_login'))

    return render_template('super_admin_login.html')

@app.route('/super_admin_dashboard', methods=['GET'])
def super_admin_dashboard():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('super_admin_login'))

    num_companies = companies_collection.count_documents({})
    num_universities = universities_collection.count_documents({})
    num_students = students_collection.count_documents({})
    
    # Get collaboration count (projects that are completed)
    num_collaborations = projects_collection.count_documents({"status": "completed"})

    return render_template('superadmin.html', 
                          num_companies=num_companies, 
                          num_universities=num_universities, 
                          num_students=num_students,
                          num_collaborations=num_collaborations)

@app.route('/get_companies', methods=['GET'])
def get_companies():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify([])

    companies = list(companies_collection.find({}, {"_id": 0, "company_name": 1, "email": 1, "employee_size": 1}))
    return jsonify(companies)

@app.route('/get_universities', methods=['GET'])
def get_all_universities():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify([])

    universities = list(universities_collection.find({}))
    result = []
    
    for university in universities:
        # Count students for this university
        student_count = students_collection.count_documents({"university_name": university.get("name")})
        
        result.append({
            "id": str(university["_id"]),
            "name": university.get("name"),
            "email": university.get("email"),
            "address": university.get("address", "N/A"),
            "departments": university.get("departments", []),
            "student_count": student_count
        })
    
    return jsonify(result)

@app.route('/get_students', methods=['GET'])
def get_all_students():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify([])

    # Find all students, excluding the _id field from results by default
    students = list(students_collection.find({}, {"name": 1, "email": 1, "university_name": 1, "department": 1, "gpa": 1}))
    
    # Convert ObjectId to string for each student
    for student in students:
        student['id'] = str(student['_id'])
        del student['_id']  # Remove the original _id field
    
    return jsonify(students)

@app.route('/get_pending_requests', methods=['GET'])
def get_pending_requests():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"pending_universities": [], "pending_companies": []})

    pending_universities = list(pending_universities_collection.find({"status": "pending"}))
    for university in pending_universities:
        university['_id'] = str(university['_id'])

    pending_companies = list(pending_companies_collection.find({"status": "pending"}))
    for company in pending_companies:
        company['_id'] = str(company['_id'])

    return jsonify({"pending_universities": pending_universities, "pending_companies": pending_companies})

@app.route('/get_pending_requests_count', methods=['GET'])
def get_pending_requests_count():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"count": 0})

    pending_universities_count = pending_universities_collection.count_documents({"status": "pending"})
    pending_companies_count = pending_companies_collection.count_documents({"status": "pending"})
    total_count = pending_universities_count + pending_companies_count

    return jsonify({"count": total_count})

@app.route('/approve_company/<company_id>', methods=['POST'])
def approve_company(company_id):
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."})

    pending_company = pending_companies_collection.find_one({"_id": ObjectId(company_id)})

    if pending_company:
        # Move the company from pending to approved
        companies_collection.insert_one({
            "company_name": pending_company['company_name'],
            "email": pending_company['email'],
            "password": pending_company['password'],
            "employee_size": pending_company['employee_size'],
            "approved_at": datetime.now()
        })
        pending_companies_collection.update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"status": "approved"}}
        )
        return jsonify({"message": "Company approved successfully!"})
    else:
        return jsonify({"message": "Company not found!"})

@app.route('/reject_company/<company_id>', methods=['POST'])
def reject_company(company_id):
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."})

    pending_company = pending_companies_collection.find_one({"_id": ObjectId(company_id)})

    if pending_company:
        pending_companies_collection.update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"status": "rejected"}}
        )
        return jsonify({"message": "Company rejected successfully!"})
    else:
        return jsonify({"message": "Company not found!"})

@app.route('/approve_university/<university_id>', methods=['POST'])
def approve_university(university_id):
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."})

    pending_university = pending_universities_collection.find_one({"_id": ObjectId(university_id)})

    if pending_university:
        # Move the university from pending to approved
        universities_collection.insert_one({
            "name": pending_university['name'],
            "email": pending_university['email'],
            "password": pending_university['password'],
            "departments": pending_university['departments'],
            "approved_at": datetime.now()
        })
        pending_universities_collection.update_one(
            {"_id": ObjectId(university_id)},
            {"$set": {"status": "approved"}}
        )
        return jsonify({"message": "University approved successfully!"})
    else:
        return jsonify({"message": "University not found!"})

@app.route('/reject_university/<university_id>', methods=['POST'])
def reject_university(university_id):
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."})

    pending_university = pending_universities_collection.find_one({"_id": ObjectId(university_id)})

    if pending_university:
        pending_universities_collection.update_one(
            {"_id": ObjectId(university_id)},
            {"$set": {"status": "rejected"}}
        )
        return jsonify({"message": "University rejected successfully!"})
    else:
        return jsonify({"message": "University not found!"})

@app.route('/add_university', methods=['POST'])
def add_university():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."}), 403

    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    departments = data.get('departments', [])

    # Check if university already exists
    existing_university = universities_collection.find_one({"email": email})
    if existing_university:
        return jsonify({"message": "University with this email already exists"}), 400

    # Insert new university
    universities_collection.insert_one({
        "name": name,
        "email": email,
        "password": password,
        "departments": departments,
        "created_at": datetime.now()
    })

    return jsonify({"message": "University added successfully!"}), 201

@app.route('/add_company', methods=['POST'])
def add_company():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to perform this action."}), 403

    data = request.json
    company_name = data.get('company_name')
    email = data.get('email')
    password = data.get('password')
    employee_size = data.get('employee_size')

    # Check if company already exists
    existing_company = companies_collection.find_one({"email": email})
    if existing_company:
        return jsonify({"message": "Company with this email already exists"}), 400

    # Insert new company
    companies_collection.insert_one({
        "company_name": company_name,
        "email": email,
        "password": password,
        "employee_size": employee_size,
        "created_at": datetime.now()
    })

    return jsonify({"message": "Company added successfully!"}), 201

@app.route('/get_analytics_data', methods=['GET'])
def get_analytics_data():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify({"message": "You do not have permission to access this data."}), 403

    # Get monthly registrations for the past year
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_data = {
        "students": [0] * 12,
        "universities": [0] * 12,
        "companies": [0] * 12
    }
    
    # This is a placeholder - in a real application, you would query the database with date filters
    # For demonstration purposes, we're returning mock data
    
    return jsonify({
        "monthly_registrations": monthly_data,
        "collaboration_types": {
            "internships": 45,
            "projects": 25,
            "research": 15,
            "workshops": 15
        },
        "top_universities": [
            {"name": "University A", "placement_rate": 92},
            {"name": "University B", "placement_rate": 88},
            {"name": "University C", "placement_rate": 85},
            {"name": "University D", "placement_rate": 82},
            {"name": "University E", "placement_rate": 80}
        ],
        "top_companies": [
            {"name": "Company A", "students_hired": 45},
            {"name": "Company B", "students_hired": 40},
            {"name": "Company C", "students_hired": 35},
            {"name": "Company D", "students_hired": 30},
            {"name": "Company E", "students_hired": 25}
        ]
    })

