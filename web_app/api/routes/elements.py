"""Elements API — Text, image, and shape element operations."""
from flask import Blueprint, jsonify, request

elements_bp = Blueprint('elements', __name__)


@elements_bp.route('/<doc_id>/<int:page_num>/elements', methods=['GET'])
def list_elements(doc_id, page_num):
    return jsonify({'doc_id': doc_id, 'page': page_num, 'elements': []})


@elements_bp.route('/<doc_id>/<int:page_num>/elements', methods=['POST'])
def add_element(doc_id, page_num):
    data = request.get_json(force=True) or {}
    return jsonify({'status': 'added', 'element': data, 'page': page_num}), 201


@elements_bp.route('/<doc_id>/<int:page_num>/elements/<element_id>', methods=['PUT'])
def update_element(doc_id, page_num, element_id):
    data = request.get_json(force=True) or {}
    return jsonify({'status': 'updated', 'element_id': element_id, 'changes': data})


@elements_bp.route('/<doc_id>/<int:page_num>/elements/<element_id>', methods=['DELETE'])
def delete_element(doc_id, page_num, element_id):
    return jsonify({'status': 'deleted', 'element_id': element_id})


@elements_bp.route('/<doc_id>/<int:page_num>/elements/annotate', methods=['POST'])
def annotate(doc_id, page_num):
    data = request.get_json(force=True) or {}
    return jsonify({'status': 'annotated', 'annotation': data})
