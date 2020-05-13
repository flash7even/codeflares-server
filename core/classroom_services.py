import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_classroom_tasks = 'cp_training_classroom_tasks'
_es_type = '_doc'
_es_size = 100


DELETED = 'DELETED'
EXPIRED = 'EXPIRED'
