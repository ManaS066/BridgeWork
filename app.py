from flask import Flask, render_template
from flask_pymongo import ASCENDING, PyMongo
import os

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://manasranjanpradhan2004:pRZ0F9oyRoY1FHxs@university.m80kj.mongodb.net/University?retryWrites=true&w=majority"
app.config["MONGO_URI"] = MONGO_URI

mongo = PyMongo(app)
app.secret_key = os.urandom(24)

# References to collections
db = mongo.db
universities_collection = db.universities
hod_collection = db.hods
students_collection = db.students
companies_collection = db.companies
jobs = db.jobs
super_admins_collection = db.super_admin
pending_universities_collection = db.pending_universities
pending_companies_collection = db.pending_companies
pending_companies_collection.create_index([("created_at", ASCENDING)], expireAfterSeconds=86400)
# Import routes
from routes.hod_routes import *
from routes.student_routes import *
from routes.company_routes import *
from routes.university_routes import *
from routes.superadmin_routes import *

if __name__ == '__main__':
    app.run(debug=True)