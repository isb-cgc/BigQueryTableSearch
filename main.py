###
# Copyright 2023, ISB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_talisman import Talisman
import requests
from google.cloud import bigquery, logging
from datetime import datetime
from random import randint

app = Flask(__name__)
TIER = os.environ.get('TIER', 'test')
app.config['TESTING'] = (TIER.lower() != 'prod')
app.config['ENV'] = 'production' if TIER.lower() == 'prod' else 'development'

# length of time (in seconds) the browser will respect the HSTS header
# production and UAT should be set to 31,536,000 seconds (by not setting any HSTS_MAX_age,
# else set to 3600 (test and dev)
hsts_max_age = int(os.environ.get('HSTS_MAX_AGE') or 3600)

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

GOOGLE_APPLICATION_CREDENTIALS = os.path.join(app.root_path, 'privatekey.json')
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
logging_client = logging.Client()
bq_total_entries = 0
BQ_ECOSYS_BUCKET = os.environ.get('BQ_ECOSYS_BUCKET',
                                  'https://storage.googleapis.com/webapp-static-files-isb-cgc-dev/bq_ecosys/')
BQ_FILTER_FILE_NAME = 'bq_meta_filters.json'
BQ_FILTER_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_FILTER_FILE_NAME
BQ_METADATA_FILE_NAME = 'bq_meta_data.json'
BQ_METADATA_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_METADATA_FILE_NAME
BQ_USEFUL_JOIN_FILE_NAME = 'bq_useful_join.json'
BQ_USEFUL_JOIN_FILE_PATH = BQ_ECOSYS_BUCKET + BQ_USEFUL_JOIN_FILE_NAME

bq_table_files = {
    'bq_filters': {'last_modified': None, 'file_path': BQ_FILTER_FILE_PATH,
                   'file_data': None},
    'bq_metadata': {'last_modified': None, 'file_path': BQ_METADATA_FILE_PATH,
                    'file_data': None},
    'bq_useful_join': {'last_modified': None, 'file_path': BQ_USEFUL_JOIN_FILE_PATH,
                       'file_data': None}
}


@app.route("/", methods=['POST', 'GET'])
def home():
    return redirect(url_for('search', status='current'))


@app.route("/faq/")
def faq():
    return render_template("faq.html")


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/privacy/")
def privacy():
    return render_template("privacy.html")


@app.route("/search", methods=['POST', 'GET'])
def search(status=None):
    if not bq_table_files['bq_filters']['file_data']:
        setup_app()
    selected_filters = {}
    if request.method == 'POST':
        rq_meth = request.form
    else:
        rq_meth = request.args
    for f in ['projectId', 'datasetId', 'tableId', 'friendlyName', 'description', 'field_name', 'labels',
              'status', 'category', 'experimental_strategy', 'program', 'source', 'data_type', 'reference_genome']:
        if rq_meth.get(f):
            selected_filters[f] = request.args.get(f).lower()
    return render_template("bq_meta_search.html", bq_filters=bq_table_files['bq_filters']['file_data'],
                           selected_filters=selected_filters,
                           bq_total_entries=bq_total_entries)


@app.route("/search_api", methods=['GET', 'POST'])
def search_api():
    setup_app()
    filtered_meta_data = []
    if bq_table_files['bq_metadata']['file_data']:
        filtered_meta_data = filter_rows(bq_table_files['bq_metadata']['file_data'], request)
    return jsonify(filtered_meta_data)


@app.route("/get_tbl_preview/<proj_id>/<dataset_id>/<table_id>/", methods=['GET', 'POST'])
def get_tbl_preview(proj_id, dataset_id, table_id):
    status = 200
    max_row = 8
    try:
        if not proj_id or not dataset_id or not table_id:
            app.logger.warning("[WARNING] Required ID missing: {}.{}.{}".format(proj_id, dataset_id, table_id))
            status = 400
            result = {
                'message': "One or more required parameters (project id, dataset_id or table_id) were not supplied."
            }
        else:
            client = bigquery.Client(project=proj_id)
            rows_iter = client.list_rows(f'{proj_id}.{dataset_id}.{table_id}', max_results=max_row)
            if rows_iter and rows_iter.total_rows:
                schema_fields = [schema.to_api_repr() for schema in list(rows_iter.schema)]
                tbl_data = [dict(row) for row in list(rows_iter)]
                result = {
                    'tbl_data': tbl_data,
                    'schema_fields': schema_fields
                }

            else:
                status = 204
                result = {
                    'message': f'No record has been found for table {proj_id}.{dataset_id}.{table_id}.'
                }

    except ValueError as e:
        status = e.response.status_code
        result = {
            'message': "ValueError"
        }
    except Exception as e:
        status = e.response.status_code
        result = {
            'message': "Exception"
        }
    if status != 200:
        app.logger.error(
            f"ERROR While attempting to retrieve preview data for {proj_id}.{dataset_id}.{table_id} table: [{status}] {result['message']}")
    return jsonify(result)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def filter_by_prop(rq_meth, rows, attr_list, sub_category, exact_match_search):
    for attr in attr_list:
        f_vals = rq_meth.get(attr, '').strip().lower()
        if f_vals:
            filtered_rows = []
            for row in rows:
                add_row = False
                if sub_category:
                    field_dict = row.get(sub_category)
                    if field_dict:
                        if sub_category == 'labels':
                            for k in field_dict.keys():
                                for f_val in f_vals.split('|'):
                                    if k.startswith(attr):
                                        if exact_match_search:
                                            if field_dict.get(k).lower() == f_val:
                                                add_row = True
                                                break
                                        else:
                                            if f_val in field_dict.get(k).lower():
                                                add_row = True
                                                break
                                if add_row:
                                    break
                        else:
                            for f_val in f_vals.split('|'):
                                if exact_match_search:
                                    if field_dict.get(attr).lower() == f_val:
                                        add_row = True
                                        break
                                else:
                                    if f_val in field_dict.get(attr).lower():
                                        add_row = True
                                        break
                else:
                    for f_val in f_vals.split('|'):
                        if exact_match_search:
                            add_row = (row.get(attr).lower() == f_val)
                        else:
                            add_row = (row.get(attr) and f_val in row.get(attr).lower())
                        if add_row:
                            break
                if add_row:
                    filtered_rows.append(row)
            rows = filtered_rows
    return rows


def search_field(field_list, f_val, is_field_found):
    for field in field_list:
        is_field_found = (f_val in field['name'].lower())
        if is_field_found:
            break
        elif 'fields' in field:
            is_field_found = search_field(field['fields'], f_val, is_field_found)
            if is_field_found:
                break
    return is_field_found


def filter_by_field_name(rq_meth, rows):
    f_val = rq_meth.get('field_name', '').strip().lower()
    if f_val:
        filtered_rows = []
        for row in rows:
            field_dict = row.get('schema')
            if field_dict:
                field_list = field_dict.get('fields')
                is_field_found = search_field(field_list, f_val, False)
                if is_field_found:
                    filtered_rows.append(row)
        rows = filtered_rows
    return rows


def filter_by_all_labels(rq_meth, rows):
    f_val = rq_meth.get('labels', '').strip().lower()
    if f_val:
        filtered_rows = []
        for row in rows:
            label_dict = row.get('labels')
            if label_dict:
                for val in label_dict.values():
                    if val.lower() == f_val:
                        filtered_rows.append(row)
                        break
        rows = filtered_rows
    return rows


def filter_rows(rows, req):
    if req.method == 'POST':
        rq_meth = req.form
    else:
        rq_meth = req.args
    generic_filters = ['description', 'friendlyName']
    tbl_ref_filters = ['projectId']
    tbl_ref_filters2 = ['datasetId', 'tableId']
    label_filters = ['status', 'category', 'experimental_strategy', 'data_type', 'source', 'program',
                     'reference_genome']

    filter_prop_list = [{'attr_list': generic_filters, 'subcategory': None, 'is_exact_match': False},
                        {'attr_list': tbl_ref_filters, 'subcategory': 'tableReference', 'is_exact_match': True},
                        {'attr_list': tbl_ref_filters2, 'subcategory': 'tableReference', 'is_exact_match': False},
                        {'attr_list': label_filters, 'subcategory': 'labels', 'is_exact_match': True}]
    for filter_prop in filter_prop_list:
        rows = filter_by_prop(rq_meth, rows, filter_prop['attr_list'], filter_prop['subcategory'],
                              filter_prop['is_exact_match'])
    rows = filter_by_field_name(rq_meth, rows)
    rows = filter_by_all_labels(rq_meth, rows)

    return rows


def get_schema_fields(schema_field):
    nested_schema_dic = {}
    if schema_field.fields:
        for field in schema_field.fields:
            if schema_field.name in nested_schema_dic.keys():
                nested_schema_dic[schema_field.name].append(get_schema_fields(field))
            else:
                nested_schema_dic[schema_field.name] = [get_schema_fields(field)]
        return nested_schema_dic
    else:
        return schema_field.name


def setup_app():
    global bq_table_files, bq_total_entries
    status_code = 200
    try:
        is_bq_metadata_updated = False
        is_useful_join_updated = False
        for f in bq_table_files:
            r = requests.head(bq_table_files[f]['file_path'] + '?t=' + str(randint(1000, 9999)))
            r.raise_for_status()
            file_last_modified = datetime.strptime(r.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S GMT')
            if not bq_table_files[f]['file_data'] or \
                    not bq_table_files[f]['last_modified'] or (
                    bq_table_files[f]['last_modified'] and (bq_table_files[f]['last_modified'] < file_last_modified)):
                bq_table_files[f]['last_modified'] = file_last_modified
                bq_table_files[f]['file_data'] = requests.get(bq_table_files[f]['file_path']).json()
                is_bq_metadata_updated = (not is_bq_metadata_updated and f == 'bq_metadata')
                is_useful_join_updated = (not is_useful_join_updated and f == 'bq_useful_join')
        bq_total_entries = len(bq_table_files['bq_metadata']['file_data']) if bq_table_files['bq_metadata'][
            'file_data'] else 0
        if (is_bq_metadata_updated and bq_total_entries) or is_useful_join_updated:
            for bq_meta_data_row in bq_table_files['bq_metadata']['file_data']:
                useful_joins = []
                row_id = bq_meta_data_row['id']
                for join in bq_table_files['bq_useful_join']['file_data']:
                    if join['id'] == row_id:
                        useful_joins = join['joins']
                        break
                bq_meta_data_row['usefulJoins'] = useful_joins
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
        app.logger.error(f'ERROR While attempting to retrieve BQ metadata file: [{status_code}] {error_message}')


setup_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
else:
    logging_client.logger('app_login_log')
    logging_client.setup_logging()
