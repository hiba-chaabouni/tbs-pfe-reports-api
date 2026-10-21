"""One JSON error format for the whole API:

    {"error": "<short name>", "message": "<clear explanation>", "status": <code>}
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Raise this anywhere in the code to stop and return a JSON error."""

    def __init__(self, status, error, message):
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


def error_response(status, error, message):
    body = {"error": error, "message": message, "status": status}
    return jsonify(body), status


def register_error_handlers(app):
    # Our own errors (raised with ApiError).
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return error_response(e.status, e.error, e.message)

    # Flask/Werkzeug errors: unknown route (404), wrong method (405), etc.
    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        messages = {
            404: "The requested URL does not exist on this API.",
            405: "This HTTP method is not allowed on this URL.",
        }
        return error_response(e.code, e.name, messages.get(e.code, e.description))

    # Anything unexpected: generic 500, never a stack trace.
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.exception("Unhandled error")  # full details stay in the server console
        return error_response(500, "Internal Server Error",
                              "Something went wrong on the server. Please try again later.")
