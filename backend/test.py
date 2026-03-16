from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route("/api/test")
def test():
    return jsonify({"status": "Flask is working!"})

if __name__ == "__main__":
    app.run(debug=True, port=5002)