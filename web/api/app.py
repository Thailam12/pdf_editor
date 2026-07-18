"""Flask application factory — wires all API blueprints together."""
from flask import Flask
from flask_cors import CORS

def create_app(config=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = '/app/uploads'

    if config:
        app.config.update(config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from web_app.api.routes.documents import documents_bp
    from web_app.api.routes.ai import ai_bp
    from web_app.api.routes.pages import pages_bp
    from web_app.api.routes.elements import elements_bp
    from web_app.api.routes.search import search_bp
    from web_app.api.routes.compare import compare_bp

    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(pages_bp, url_prefix='/api/pages')
    app.register_blueprint(elements_bp, url_prefix='/api/elements')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(compare_bp, url_prefix='/api/compare')

    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0'}

    return app
