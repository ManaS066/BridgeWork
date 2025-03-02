from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from app import app, companies_collection, universities_collection, students_collection, super_admins_collection, pending_universities_collection, pending_companies_collection
from bson.objectid import ObjectId  # Import ObjectId

@app.route('/super_admin_dashboard', methods=['GET'])
def super_admin_dashboard():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('super_admin_login'))

    num_companies = companies_collection.count_documents({})
    num_universities = universities_collection.count_documents({})
    num_students = students_collection.count_documents({})

    return render_template('super_admin_dashboard.html', num_companies=num_companies, num_universities=num_universities, num_students=num_students)

@app.route('/get_companies', methods=['GET'])
def get_companies():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify([])

    companies = list(companies_collection.find({}, {"_id": 0, "company_name": 1, "email": 1, "employee_size": 1}))
    return jsonify(companies)


@app.route('/get_students', methods=['GET'])
def get_students():
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return jsonify([])

    students = list(students_collection.find({}, {"_id": 0, "name": 1, "email": 1, "university_name": 1}))
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
            "employee_size": pending_company['employee_size']
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
            "departments": pending_university['departments']
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

@app.route('/super_admin_login', methods=['GET', 'POST'])
def super_admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        super_admin = super_admins_collection.find_one({"email": email, "password": password})
        
        if super_admin :
            session['user_id'] = str(super_admin['_id'])
            session['user_role'] = 'super_admin'
            session['user_name'] = super_admin['name']
            return redirect(url_for('super_admin_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('super_admin_login'))

    return render_template('super_admin_login.html')