from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://manasranjanpradhan2004:pRZ0F9oyRoY1FHxs@university.m80kj.mongodb.net/University?retryWrites=true&w=majority"
app.config["MONGO_URI"] = MONGO_URI

mongo = PyMongo(app)


# References to collections
db = mongo.db
universities_collection = db.universities
hod_collection = db.hods  # Collection to store HOD data
students_collection = db.students 
@app.route('/hod_register', methods=['GET'])
def hod_register_page():
    return render_template('hod_register.html')

@app.route('/get_universities', methods=['GET'])
def get_universities():
    universities = universities_collection.find({}, {"_id": 1, "name": 1})
    return jsonify([{"id": str(u["_id"]), "name": u["name"]} for u in universities])

@app.route('/get_departments/<university_id>', methods=['GET'])
def get_departments(university_id):
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    if university:
        return jsonify(university.get("departments", []))
    return jsonify([])

@app.route('/register_hod', methods=['POST'])
def register_hod():
    data = request.json
    university_id = data.get('universityId')
    department = data.get('department')
    email = data.get('email')
    password = data.get('password')  # In production, store hashed passwords

    if not university_id or not department or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    hod_id = hod_collection.insert_one({
        "university_id": university_id,
        "department": department,
        "email": email,
        "password": password  # Hash in production
    }).inserted_id

    return jsonify({
        "message": "HOD registered successfully!",
        "hod_id": str(hod_id)
    })


@app.route('/student_register', methods=['GET'])
def student_register_page():
    return render_template('student_register.html')


@app.route('/register_student', methods=['POST'])
def register_student():
    university_id = request.form.get('universityId')
    department = request.form.get('department')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password') 
    rollno = request.form.get('roll_number')
    registration_no = request.form.get('reg_number')
     # In production, hash this
    

    if not all([university_id, department, name, email, password,rollno,registration_no]):
        return jsonify({"message": "All fields are required"}), 400

    # Save document
    

    student_id = students_collection.insert_one({
        "university_id": university_id,
        "department": department,
        "name": name,
        "email": email,
        "password": password, 
         "rollno":rollno,
         "registration_no":registration_no,
           # Hash in production
       
    }).inserted_id

    return jsonify({
        "message": "Student registered successfully!",
        "student_id": str(student_id)
    })

if __name__ == '__main__':
    app.run(debug=True)
