from functools import wraps

from flask_jwt_extended import verify_jwt_in_request, get_jwt_claims

role_levels = ['contestant', 'service', 'moderator', 'manager', 'admin', 'root']

role_order = {
    'contestant': 1,
    'service': 2,
    'moderator': 3,
    'manager': 4,
    'admin': 8,
    'root': 10,
}


def access_required(access='ALL'):
    def callable(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt_claims()
            print('claims: ', claims)
            if 'ALL' not in access:
                access_roles = access.split()
                if len(access_roles) > 0:
                    required_role = access_roles[0]
                    required_role_order = role_order.get(required_role, 0)
                    user_role = claims['role']
                    user_role_order = role_order.get(user_role, 0)
                    print(f'required_role_order: {required_role_order}, user_role_order: {user_role_order}')
                    if user_role_order < required_role_order:
                        claim_role = claims['role']
                        return {"message": f'{claim_role} does not have access to this api'}, 403
            return fn(*args, **kwargs)
        return wrapper
    return callable
