import json
from flask import jsonify

def success_response(data=None, message="Success", status_code=200):
    """Create a standardized success response"""
    response = {
        'success': True,
        'message': message,
        'data': data or {}
    }
    return jsonify(response), status_code

def error_response(message="Error", code="ERROR", status_code=400, details=None):
    """Create a standardized error response"""
    response = {
        'success': False,
        'error': message,
        'code': code,
        'details': details
    }
    return jsonify(response), status_code