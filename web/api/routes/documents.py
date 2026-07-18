"""Documents API — CRUD operations on PDF documents."""
from flask import Blueprint, jsonify, request

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/', methods=['GET'])
def list_documents():
    return jsonify({'documents': [], 'total': 0})


@documents_bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    return jsonify({'id': doc_id, 'pages': 0, 'title': ''})


@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    return jsonify({'id': 'new-doc', 'filename': file.filename, 'status': 'uploaded'}), 201


@documents_bp.route('/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    return jsonify({'status': 'deleted', 'id': doc_id})


@documents_bp.route('/<doc_id>/save', methods=['POST'])
def save_document(doc_id):
    return jsonify({'status': 'saved', 'id': doc_id})
