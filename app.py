from flask import Flask
from employees.routes import employee_bp

app = Flask(__name__)
app.register_blueprint(employee_bp, url_prefix='/peoplesuite/apis/employees')

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
