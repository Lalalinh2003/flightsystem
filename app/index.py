from flask import Flask, render_template, redirect, url_for
flightapp = Flask(__name__)

#Duong dan den trang chu
@flightapp.route("/")
def home():
    return render_template("home.html")

#Duong dan den trang dang nhap
@flightapp.route("/login")
def login():
    return render_template("login.html")

#Duong dan den trang dat ve
@flightapp.route("/booktickets")
def booktickets():
    return render_template("booktickets.html")

if __name__ == '__main__':
    flightapp.run(debug=True)

