from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)

# MongoDB Configuration (Replace <your_connection_string> with actual MongoDB URI)
app.config["MONGO_URI"] = "mongodb+srv://manasranjanpradhan2004:pRZ0F9oyRoY1FHxs@university.m80kj.mongodb.net/?retryWrites=true&w=majority&appName=University"  # Change if using a cloud DB
mongo = PyMongo(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')  # Store securely using hashing in real apps
    num_departments = int(data.get('numDepartments', 0))
    departments = data.get('departments', [])

    # Insert university data
    university_id = mongo.db.universities.insert_one({
        "name": name,
        "email": email,
        "password": password,  # Hashing recommended for production
        "num_departments": num_departments,
        "departments": departments
    }).inserted_id

    return jsonify({
        "message": "University registered successfully!",
        "university_id": str(university_id)
    })

if __name__ == '__main__':
    app.run(debug=True)
