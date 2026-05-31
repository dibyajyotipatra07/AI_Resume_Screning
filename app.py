from flask import Flask, render_template, request, redirect
app = Flask(__name__)
@app.route('/')
def home():
    return render_template('login_page.html')

app.run(debug=True)