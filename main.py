###
# Copyright 2025, ISB
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
import requests
from google.cloud import bigquery, logging
from google.api_core.exceptions import BadRequest
import bq_builder
import settings
import concurrent.futures
import json

app = Flask(__name__)

if os.environ.get('IS_GAE_DEPLOYMENT', 'False') != 'True':
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(app.root_path, 'privatekey.json')
logging_client = logging.Client()


@app.route("/", methods=['POST', 'GET'])
def home():
    return redirect(url_for('search', status='current', include_always_newest='false'))


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/privacy/")
def privacy():
    return render_template("privacy.html")


@app.route("/search", methods=['POST', 'GET'])
def search(status=None):
    error_msg = settings.pull_metadata()
    if error_msg:
        app.logger.error(f"[ERROR] {error_msg}")
    selected_filters = {}
    if request.method == 'POST':
        rq_meth = request.form
    else:
        rq_meth = request.args
    for f in ['projectId', 'datasetId', 'tableId', 'friendlyName', 'description', 'field_name', 'labels',
              'include_always_newest', 'status', 'category', 'experimental_strategy', 'program', 'source', 'data_type',
              'reference_genome']:
        if rq_meth.get(f):
            selected_filters[f] = request.args.get(f).lower()
    return render_template("bq_meta_search.html", bq_filters=settings.bq_table_files['bq_filters']['file_data'],
                           selected_filters=selected_filters,
                           bq_total_entries=settings.bq_total_entries)


@app.route("/search_api", methods=['GET', 'POST'])
def search_api():
    error_msg = settings.pull_metadata()
    if error_msg:
        app.logger.error(f"[ERROR] {error_msg}")
    filtered_meta_data = []
    try:
        query_statement = bq_builder.metadata_query(request)
        # print(query_statement)
        bigquery_client = bigquery.Client(project=settings.BQ_METADATA_PROJ)
        query_job = bigquery_client.query(query_statement)

        result = query_job.result(timeout=30)
        filtered_meta_data = [json.loads(dict(row)['metadata']) for row in result]
    except ValueError:
        error_msg = 'An invalid query parameter was detected. Please revise your search criteria and search again.'
    except (concurrent.futures.TimeoutError, requests.exceptions.ReadTimeout):
        error_msg = "Sorry, query job has timed out."
    except (BadRequest, Exception) as e:
        error_msg = "There was an error during the download process."
    if error_msg:
        app.logger.error(f"[ERROR] {error_msg}")
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


settings.setup_app(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
