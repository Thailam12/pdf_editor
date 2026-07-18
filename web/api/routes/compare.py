"""Compare API — Document comparison and diff generation."""
from flask import Blueprint, jsonify, request

compare_bp = Blueprint('compare', __name__)


@compare_bp.route('/', methods=['POST'])
def compare_documents():
    data = request.get_json(force=True) or {}
    doc_a = data.get('document_a')
    doc_b = data.get('document_b')
    return jsonify({
        'document_a': doc_a,
        'document_b': doc_b,
        'diff': [],
        'summary': {'added': 0, 'removed': 0, 'modified': 0}
    })


@compare_bp.route('/visual/<doc_id_a>/<doc_id_b>', methods=['GET'])
def visual_diff(doc_id_a, doc_id_b):
    return jsonify({
        'document_a': doc_id_a,
        'document_b': doc_id_b,
        'pages': [],
        'highlight_color': '#ff0000'
    })


@compare_bp.route('/text/<doc_id_a>/<doc_id_b>', methods=['GET'])
def text_diff(doc_id_a, doc_id_b):
    return jsonify({
        'document_a': doc_id_a,
        'document_b': doc_id_b,
        'diff': [],
        'unified': ''
    })
