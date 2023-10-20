from flask import Flask, jsonify


app = Flask(__name__)

@app.route('/')
def return_values():

    return (jsonify({"msg" : "hello world",
                    "date" : "27.11.2022"}))

    
app.run(host="0.0.0.0")