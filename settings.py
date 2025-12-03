import os
from os import getenv
from flask_talisman import Talisman
import requests
from random import randint
from datetime import datetime

hsts_max_age = int(getenv('HSTS_MAX_AGE') or 3600)
TIER = getenv('TIER', 'dev')
IS_LOCAL = bool(getenv('IS_LOCAL','False').lower() == 'true')
BQ_METADATA_PROJ = getenv('BQ_METADATA_PROJ', 'isb-cgc-dev-1')
BQ_ECOSYS_BUCKET = getenv('BQ_ECOSYS_BUCKET',
                                  'https://storage.googleapis.com/webapp-static-files-isb-cgc-dev/bq_ecosys/')
BQ_FILTER_FILE_NAME = 'bq_meta_filters.json'
BQ_FILTER_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_FILTER_FILE_NAME
BQ_METADATA_FILE_NAME = 'bq_meta_data.json'
BQ_METADATA_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_METADATA_FILE_NAME

bq_table_files = {
    'bq_filters': {'last_modified': None, 'file_path': BQ_FILTER_FILE_PATH,
                   'file_data': None},
    'bq_metadata': {'last_modified': None, 'file_path': BQ_METADATA_FILE_PATH,
                    'file_data': None}
}
bq_total_entries = 0


# setup application
def setup_app(app):
    app.config['TESTING'] = (TIER.lower() != 'prod')
    app.config['ENV'] = 'production' if TIER.lower() == 'prod' else 'development'
    if not IS_LOCAL:
        Talisman(app, strict_transport_security_max_age=hsts_max_age, content_security_policy={
            'default-src': [
                '\'self\'',
                '*.googletagmanager.com',
                '*.google-analytics.com',
                '*.googleapis.com',
                "*.fontawesome.com",
                '*.jsdelivr.net',
                '\'unsafe-inline\'',
                'data:',
                'blob:'
            ],
            'font-src': ['\'self\'', '*.gstatic.com']
        })


# checks the last modified dates of bq filter and bq metadata files from the bucket
# and fetches the file data if the cached file data is outdated
def pull_metadata():
    global bq_table_files, bq_total_entries
    status_code = 200
    try:
        is_bq_metadata_updated = False
        for f in bq_table_files:
            r = requests.head(bq_table_files[f]['file_path'] + '?t=' + str(randint(1000, 9999)))
            r.raise_for_status()
            file_last_modified = datetime.strptime(r.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S GMT')
            if not bq_table_files[f]['file_data'] or \
                    not bq_table_files[f]['last_modified'] or (
                    bq_table_files[f]['last_modified'] and (bq_table_files[f]['last_modified'] < file_last_modified)):
                bq_table_files[f]['last_modified'] = file_last_modified
                bq_table_files[f]['file_data'] = requests.get(bq_table_files[f]['file_path']).json()
                if f == 'bq_metadata':
                    is_bq_metadata_updated = (not is_bq_metadata_updated)
        bq_total_entries = len(bq_table_files['bq_metadata']['file_data']) if bq_table_files['bq_metadata'][
            'file_data'] else 0
    except requests.exceptions.HTTPError as e:
        error_message = 'HTTPError'
        status_code = e.response.status_code
    except requests.exceptions.ReadTimeout as e:
        error_message = 'ReadTimeout'
        status_code = e.response.status_code
    except requests.exceptions.ConnectionError as e:
        error_message = 'ConnectionError'
        status_code = e.response.status_code
    message = None
    if status_code != 200:
        bq_table_files['bq_filters']['file_data'] = None
        bq_table_files['bq_metadata']['file_data'] = None
        bq_total_entries = 0
        message = f'ERROR While attempting to retrieve BQ metadata file: [{status_code}] {error_message}'
    return message
