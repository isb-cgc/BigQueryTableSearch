from os import getenv
# import bq_builder
from flask_talisman import Talisman
import requests
from random import randint
from datetime import datetime
import re

hsts_max_age = int(getenv('HSTS_MAX_AGE') or 3600)
TIER = getenv('TIER', 'dev')
BQ_METADATA_PROJ = getenv('BQ_METADATA_PROJ', 'isb-cgc-dev-1')
BQ_ECOSYS_BUCKET = getenv('BQ_ECOSYS_BUCKET',
                                  'https://storage.googleapis.com/webapp-static-files-isb-cgc-dev/bq_ecosys/')
BQ_FILTER_FILE_NAME = 'bq_meta_filters.json'
BQ_FILTER_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_FILTER_FILE_NAME
BQ_METADATA_FILE_NAME = 'bq_meta_data.json'
BQ_METADATA_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_METADATA_FILE_NAME
BQ_USEFUL_JOIN_FILE_NAME = 'bq_useful_join.json'
BQ_USEFUL_JOIN_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_USEFUL_JOIN_FILE_NAME
BQ_VERSIONS_FILE_NAME = 'bq_versions.json'
BQ_VERSIONS_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_VERSIONS_FILE_NAME
BQ_MARKED_TABLE_MAP_FILE_NAME = 'bq_marked_tbl_map.json'
BQ_MARKED_TABLE_MAP_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_MARKED_TABLE_MAP_FILE_NAME

bq_table_files = {
    'bq_filters': {'last_modified': None, 'file_path': BQ_FILTER_FILE_PATH,
                   'file_data': None},
    'bq_metadata': {'last_modified': None, 'file_path': BQ_METADATA_FILE_PATH,
                    'file_data': None},
    'bq_useful_join': {'last_modified': None, 'file_path': BQ_USEFUL_JOIN_FILE_PATH,
                       'file_data': None},
    'bq_versions': {'last_modified': None, 'file_path': BQ_VERSIONS_FILE_PATH,
                    'file_data': None},
    'bq_marked_table_map': {'last_modified': None, 'file_path': BQ_MARKED_TABLE_MAP_FILE_PATH, 'file_data': None}
}
bq_total_entries = 0


def setup_app(app):
    app.config['TESTING'] = (TIER.lower() != 'prod')
    app.config['ENV'] = 'production' if TIER.lower() == 'prod' else 'development'
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
        ]
    })


def pull_metadata():
    global bq_table_files, bq_total_entries
    status_code = 200
    try:
        is_bq_metadata_updated = False
        is_useful_join_updated = False
        is_version_file_updated = False
        is_version_map_file_updated = False
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
                elif f == 'bq_useful_join':
                    is_useful_join_updated = not is_useful_join_updated
                elif f == 'bq_versions':
                    is_version_file_updated = not is_version_file_updated
                elif f == 'bq_marked_table_map':
                    is_version_map_file_updated = not is_version_map_file_updated
        bq_total_entries = len(bq_table_files['bq_metadata']['file_data']) if bq_table_files['bq_metadata'][
            'file_data'] else 0
        if (is_bq_metadata_updated and bq_total_entries) or is_useful_join_updated or is_version_file_updated or is_version_map_file_updated:
            for bq_meta_data_row in bq_table_files['bq_metadata']['file_data']:
                useful_joins = []
                row_id = bq_meta_data_row['id']

                for join in bq_table_files['bq_useful_join']['file_data']:
                    if join['id'] == row_id:
                        useful_joins = join['joins']
                        break
                bq_meta_data_row['usefulJoins'] = useful_joins
                table_version_info = None
                if 'labels' in bq_meta_data_row and 'version' in bq_meta_data_row['labels']:
                    labeled_version = bq_meta_data_row['labels']['version']
                    split_ids = re.split(':|\.', row_id)
                    proj_id = split_ids[0]
                    tbl_ds_id = split_ids[1]
                    tbl_tbl_id = split_ids[2]
                    version_id = None
                    if tbl_tbl_id.endswith('_current'):
                        root_tbl_tbl_id = tbl_tbl_id.removesuffix('current')
                        version_id = f'{proj_id}:{tbl_ds_id}.{root_tbl_tbl_id}'
                    else:
                        if bq_table_files['bq_marked_table_map']['file_data'] and tbl_ds_id in bq_table_files['bq_marked_table_map']['file_data'][proj_id]:
                            for t in bq_table_files['bq_marked_table_map']['file_data'][proj_id][tbl_ds_id]:
                                if (t.startswith('_') and tbl_tbl_id.endswith(t)) or (t.endswith('_') and tbl_tbl_id.startswith(t)):
                                    version_id = bq_table_files['bq_marked_table_map']['file_data'][proj_id][tbl_ds_id][t]
                                    break
                        if not version_id and tbl_ds_id.endswith('_versioned'):
                            root_tbl_ds_id = tbl_ds_id.removesuffix('_versioned')
                            root_tbl_tbl_id = tbl_tbl_id.removesuffix(f'{labeled_version}'.lower())
                            root_tbl_tbl_id = root_tbl_tbl_id.removesuffix(f'{labeled_version}'.upper())
                            version_id = f'{proj_id}:{root_tbl_ds_id}.{root_tbl_tbl_id}'
                    if version_id and version_id in bq_table_files['bq_versions']['file_data']:
                        table_version_info = bq_table_files['bq_versions']['file_data'][version_id]
                bq_meta_data_row['versions'] = table_version_info
    except requests.exceptions.HTTPError as e:
        error_message = 'HTTPError'
        status_code = e.response.status_code
    except requests.exceptions.ReadTimeout as e:
        error_message = 'ReadTimeout'
        status_code = e.response.status_code
    except requests.exceptions.ConnectionError as e:
        error_message = 'ConnectionError'
        status_code = e.response.status_code
    if status_code != 200:
        bq_table_files['bq_filters']['file_data'] = None
        bq_table_files['bq_metadata']['file_data'] = None
        bq_table_files['bq_useful_join']['file_data'] = None
        bq_total_entries = 0
        return f'ERROR While attempting to retrieve BQ metadata file: [{status_code}] {error_message}'