"""Pages API — Page manipulation: reorder, delete, rotate, merge."""
from flask import Blueprint, jsonify, request

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/<doc_id>/pages', methods=['GET'])
def list_pages(doc_id):
    return jsonify({'doc_id': doc_id, 'pages': []})


@pages_bp.route('/<doc_id>/pages/reorder', methods=['POST'])
def reorder_pages(doc_id):
    data = request.get_json(force=True) or {}
    order = data.get('order', [])
    return jsonify({'status': 'reordered', 'order': order})


@pages_bp.route('/<doc_id>/pages/<int:page_num>/rotate', methods=['POST'])
def rotate_page(doc_id, page_num):
    data = request.get_json(force=True) or {}
    angle = data.get('angle', 90)
    return jsonify({'status': 'rotated', 'page': page_num, 'angle': angle})


@pages_bp.route('/<doc_id>/pages/<int:page_num>', methods=['DELETE'])
def delete_page(doc_id, page_num):
    return jsonify({'status': 'deleted', 'page': page_num})


@pages_bp.route('/<doc_id>/pages/extract', methods=['POST'])
def extract_pages(doc_id):
    data = request.get_json(force=True) or {}
    pages = data.get('pages', [])
    return jsonify({'status': 'extracted', 'pages': pages})


@pages_bp.route('/<doc_id>/pages/merge', methods=['POST'])
def merge_pages(doc_id):
    return jsonify({'status': 'merged', 'doc_id': doc_id})
