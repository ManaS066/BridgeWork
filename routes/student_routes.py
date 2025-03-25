from flask import render_template, request, session, redirect, url_for, jsonify
from app import app, students_collection, universities_collection,projects_collection
from bson.objectid import ObjectId
import os

@app.route('/student_register', methods=['GET'])
def student_register_page():
    universities = list(universities_collection.find({}))
    return render_template('student_register.html', universities=universities)


@app.route('/register_student', methods=['POST'])
def register_student():
    university_id = request.form.get('universityId')
    department = request.form.get('department')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    rollno = request.form.get('roll_number')
    registration_no = request.form.get('reg_number')
    mobile_no = request.form.get('Mobile')

    if not all([university_id, department, name, email, password, rollno, registration_no,mobile_no]):
        return jsonify({"message": "All fields are required"}), 400

    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    university_name = university["name"] if university else "Unknown University"

    student_id = students_collection.insert_one({
        "university_name": university_name,
        "department": department,
        "name": name,
        "email": email,
        "password": password,
        "rollno": rollno,
        "registration_no": registration_no,
        "mobile_no": mobile_no
    }).inserted_id

    return redirect(url_for('student_login'))

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        student = students_collection.find_one({"email": email, "password": password})

        if student:
            session['student_id'] = str(student['_id'])
            session['student_name'] = student['name']
            return redirect(url_for('student_dashboard'))
        else:
            return render_template('student_login.html', error="Invalid Email or Password")

    return render_template('student_login.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student = students_collection.find_one({"_id": ObjectId(session['student_id'])})
    student_id = session['student_id']
    assigned_project = projects_collection.find_one({"assigned_students": ObjectId(student_id)})

    if assigned_project:
        assigned_project['_id'] = str(assigned_project['_id'])

    if not student:
        return redirect(url_for('student_login'))

    return render_template('student_dashboard.html', student=student)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/save_academic_details', methods=['POST'])
def save_academic_details():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    data = request.get_json()
    gpa = data.get('gpa')
    courses = data.get('courses')
    projects = data.get('projects')

    if gpa and courses and projects:
        students_collection.update_one(
            {"_id": ObjectId(session['student_id'])},
            {"$set": {"gpa": gpa, "courses": courses, "projects": projects}}
        )
        return jsonify({"message": "Academic details saved successfully!"}), 200
    return jsonify({"message": "Failed to save academic details."}), 400

@app.route('/save_skills', methods=['POST'])
def save_skills():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    data = request.get_json()
    skills = data.get('skills')

    if skills:
        students_collection.update_one(
            {"_id": ObjectId(session['student_id'])},
            {"$set": {"skills": skills}}
        )
        return jsonify({"message": "Skills saved successfully!"}), 200
    return jsonify({"message": "Failed to save skills."}), 400

@app.route('/showAllStudent', methods=['POST'])
def showAllStudent():
    students = list(students_collection.find({}))
    for student in students:
        student['_id'] = str(student['_id'])
    return jsonify(students)

@app.route('/student_details/<student_id>', methods=['GET'])
def student_details(student_id):
    student = students_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        return jsonify({"message": "Student not found"}), 404

    return render_template('student_details.html', student=student)

