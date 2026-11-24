from flask import jsonify

def api_response(success: bool, message: str, data=None, status_code: int = 200):
    """
    Standardized JSON response envelope across all Wardrobe AI backend endpoints.
    """
    payload = {
        "success": success,
        "message": message,
        "data": data
    }
    return jsonify(payload), status_code

def success_response(message: str, data=None, status_code: int = 200):
    return api_response(True, message, data, status_code)

def error_response(message: str, data=None, status_code: int = 400):
    # If a status code integer is passed as the second positional argument, handle gracefully
    if isinstance(data, int):
        status_code = data
        data = None
    return api_response(False, message, data, status_code)

