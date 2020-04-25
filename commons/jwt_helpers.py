from functools import wraps

from flask_jwt_extended import verify_jwt_in_request, get_jwt_claims


def access_required(access='ALL'):
    def callable(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt_claims()
            if 'ALL' not in access:
                access_roles = access.split()
                user_role = claims['role']
                if user_role not in access_roles:
                    claim_role = claims['role']
                    return {"message": f'{claim_role} does not have access to this methods'}, 403
            return fn(*args, **kwargs)
        return wrapper
    return callable