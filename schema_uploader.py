import argparse
import logging
import os
import json
import time
import re
from hashlib import md5
import requests

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger('schema uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('./logs/schema_uploader.log', when='midnight', interval=1,  backupCount=30)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
handler.suffix = "%Y%m%d"
handler.extMatch = re.compile(r"^\d{8}$")
logger.addHandler(handler)

rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}

ES_HOST = 'localhost:9200'


def delete_index(index_name):
    logger.debug(f'Delete index: {index_name}')
    url = f'http://{ES_HOST}/{index_name}'
    response = rs.delete(url=url, headers=_http_headers).json()
    logger.debug(f'Delete response: {response}')


def create_index(index_name, index_data):
    data = {
        "mappings": index_data
    }
    logger.debug(f'Create index: {index_name}')
    url = f'http://{ES_HOST}/{index_name}'
    response = rs.put(url=url, json=data, headers=_http_headers).json()
    logger.debug(f'Create response: {response}')


def update_index(index_name, index_data):
    logger.debug(f'Update index: {index_name}')
    url = f'http://{ES_HOST}/{index_name}/_mapping'
    response = rs.put(url=url, json=index_data ,headers=_http_headers).json()
    logger.debug(f'Update response: {response}')


def delete_schema(dirpath):

    for dirpath, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            full_filepath = os.path.join(dirpath, filename)
            if filename.endswith('.json'):
                index_name = os.path.splitext(filename)[0]
                delete_index(index_name)


def create_schema(dirpath):
    logger.info('Create schema process starts')

    for dirpath, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            full_filepath = os.path.join(dirpath, filename)
            if filename.endswith('.json'):
                index_name = os.path.splitext(filename)[0]
                with open(full_filepath) as f:
                    index_data = json.load(f)
                    create_index(index_name, index_data)

    logger.info('Create schema process completed')


def update_schema(dirpath):
    logger.info('Update schema process starts')

    for dirpath, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            full_filepath = os.path.join(dirpath, filename)
            if filename.endswith('.json'):
                index_name = os.path.splitext(filename)[0]
                with open(full_filepath) as f:
                    index_data = json.load(f)
                    update_index(index_name, index_data)

    logger.info('Update schema process completed')

if __name__ == '__main__':
    logger.info('START RUNNING ES INDEX MIGRATION SCRIPT\n')

    parser = argparse.ArgumentParser(description='Enroll an image or by a directory of images of a person')
    parser.add_argument('--dir', help="Directory of the es schema")
    parser.add_argument('--delete', help="Set true to delete existing schema")
    parser.add_argument('--create', help="Set true to create new schema")
    parser.add_argument('--update', help="Set true to update existing schema")
    args = parser.parse_args()

    dir = None

    if args.dir:
        logger.info('Directory root of the schema')
        dir = args.dir
    else:
        logger.error('Directory not given')
        exit(1)

    if args.delete and args.delete == "true":
        logger.info('Command for deleting existing schema')
        delete_schema(args.dir)

    if args.create and args.create == "true":
        logger.info('Command for creating new schema')
        create_schema(args.dir)

    if args.update and args.update == "true":
        logger.info('Command for creating new schema')
        update_index(args.dir)