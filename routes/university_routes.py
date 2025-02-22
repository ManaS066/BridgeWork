from flask import render_template, request, session, redirect, url_for, jsonify, flash
from app import app, universities_collection, jobs
from bson.objectid import ObjectId

@app.route('/get_universities', methods=['GET'])
def get_universities():
    universities = universities_collection.find({}, {"_id": 1, "name": 1})
    return jsonify([{"id": str(u["_id"]), "name": u["name"]} for u in universities])

@app.route('/get_departments/<university_id>', methods=['GET'])
def get_departments(university_id):
    university = universities_collection.find_one({"_id": ObjectId(university_id)})
    return jsonify(university.get("departments", [])) if university else jsonify([])

@app.route('/university_login', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        university = universities_collection.find_one({"email": email, "password": password})
        
        if university:
            session['university_name'] = university['name']
            return redirect(url_for('university_dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('university_login'))

    return render_template('university_login.html')

@app.route('/university_dashboard', methods=['GET'])
def university_dashboard():
    university_name = "giet"

    if not university_name:
        return jsonify({"message": "University name is required"}), 400

    job_listings = list(jobs.find({"university_name": university_name}))

    for job in job_listings:
        job['_id'] = str(job['_id'])
    
    return render_template('university_dashboard.html', university_name=university_name, job_listings=job_listings)

@app.route('/approve_job/<job_id>', methods=['POST'])
def approve_job(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id)})

    if job:
        jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"flag": 1}})
        flash("Job approved successfully!", "success")
    else:
        flash("Job not found!", "danger")
    
    university_name = job.get('university_name', '')
    return redirect(url_for('university_dashboard', university_name=university_name))