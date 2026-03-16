from flask import Flask
from flask_cors import CORS
from extensions import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    from routes.auth_routes import auth_bp
    from routes.voter_routes import voter_bp
    from routes.admin_routes import admin_bp
    from routes.blockchain_routes import blockchain_bp

    app.register_blueprint(auth_bp,       url_prefix="/api/auth")
    app.register_blueprint(voter_bp,      url_prefix="/api/voter")
    app.register_blueprint(admin_bp,      url_prefix="/api/admin")
    app.register_blueprint(blockchain_bp, url_prefix="/api/blockchain")

    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
