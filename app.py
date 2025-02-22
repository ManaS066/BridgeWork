from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, World!"

@app.route("/UnivesityLogin")
def login():
    return "Login Page"





if __name__ == '__main__':
    app.run(debug=True)
