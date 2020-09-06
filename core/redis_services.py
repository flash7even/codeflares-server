import time
import json
import requests
from datetime import timedelta
from flask import current_app as app

from extensions.flask_redis import redis_store


def check_pending_job(user_id):
    redis_user_pending_job_key = f'{app.config["REDIS_PREFIX_USER_PENDING_JOB"]}:{user_id}'
    if redis_store.connection.exists(redis_user_pending_job_key):
        return True
    else:
        return False


def add_pending_job(user_id):
    redis_user_pending_job_key = f'{app.config["REDIS_PREFIX_USER_PENDING_JOB"]}:{user_id}'
    redis_store.connection.set(redis_user_pending_job_key, 1)


def remove_pending_job(user_id):
    redis_user_pending_job_key = f'{app.config["REDIS_PREFIX_USER_PENDING_JOB"]}:{user_id}'
    redis_store.connection.delete(redis_user_pending_job_key)


def add_new_job(user_id):
    redis_user_job_key = f'{app.config["REDIS_PREFIX_USER_JOB"]}:{user_id}'
    user_job_limit = int(app.config["REDIS_PREFIX_USER_JOB_LIMIT"])

    if check_pending_job(user_id):
        return False

    if redis_store.connection.exists(redis_user_job_key):
        job_count = int(redis_store.connection.get(redis_user_job_key))
        if job_count < user_job_limit:
            redis_store.connection.incr(redis_user_job_key, 1)
            add_pending_job(user_id)
            return True
        else:
            return False
    else:
        redis_store.connection.set(redis_user_job_key, 1, timedelta(minutes=app.config["REDIS_PREFIX_USER_JOB_TIMEOUT"]))
        add_pending_job(user_id)
        return True
