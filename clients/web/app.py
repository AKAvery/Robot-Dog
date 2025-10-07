from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/functions')
def functions():
    return render_template('functions.html')

if __name__ == '__main__':
    app.run(port = 4000, debug=True)
    #app.run(debug=False,host='0.0.0.0')
