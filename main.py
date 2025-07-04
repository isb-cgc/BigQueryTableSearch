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
import swagger_config
import concurrent.futures
import json
from flasgger import Swagger
from flasgger import swag_from


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
    if request.method == 'POST':
        rq_meth = request.form
    else:
        rq_meth = request.args
    selected_filters = rq_meth.to_dict(flat=False)
    return render_template("bq_meta_search.html", bq_filters=settings.bq_table_files['bq_filters']['file_data'],
                           selected_filters=selected_filters,
                           bq_total_entries=settings.bq_total_entries)

@swag_from('api_docs/search_api_get.yaml', endpoint='search_api', methods=['GET'])
@swag_from('api_docs/search_api_post.yaml', endpoint='search_api', methods=['POST'])
@app.route("/search_api", methods=['GET', 'POST'])
def search_api():
    error_msg = settings.pull_metadata()
    if error_msg:
        app.logger.error(f"[ERROR] {error_msg}")
    filtered_meta_data = []
    try:
        query_statement = bq_builder.metadata_query(request)
        bigquery_client = bigquery.Client(project=settings.BQ_METADATA_PROJ)
        query_job = bigquery_client.query(query_statement)

        result = query_job.result(timeout=30)
        filtered_meta_data = [json.loads(dict(row)['metadata']) for row in result]
    except ValueError:
        error_msg = 'An invalid query parameter was detected. Please revise your search criteria and search again.'
        error_code = 400
    except (concurrent.futures.TimeoutError, requests.exceptions.ReadTimeout):
        error_msg = "Sorry, query job has timed out."
        error_code = 408
    except (BadRequest, Exception) as e:
        error_msg = "There was an error during the search."
        error_code = 400
    if error_msg:
        app.logger.error(f"[ERROR] {error_msg}")
        response = jsonify({'message': error_msg})
        response.status_code = error_code
        return response
    return jsonify(filtered_meta_data)


@swag_from('api_docs/get_tbl_preview.yaml', endpoint='get_tbl_preview', methods=['GET'])
@app.route("/get_tbl_preview/<proj_id>/<dataset_id>/<table_id>/", methods=['GET'])
def get_tbl_preview(proj_id, dataset_id, table_id):
    status = 200
    max_row = 8
    try:
        if not proj_id or not dataset_id or not table_id:
            app.logger.warning("[WARNING] Required ID missing")
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
        print(e)
    if status != 200:
        app.logger.error(
            f"ERROR While attempting to retrieve preview data for {proj_id}.{dataset_id}.{table_id} table: [{status}] {result['message']}")
    response = jsonify(result)
    response.status_code = status
    return response


@swag_from('api_docs/get_filter_options.yaml', endpoint='get_filter_options', methods=['GET'])
@app.route("/get_filter_options/<filter_type>/", methods=['GET'])
def get_filter_options(filter_type):
    status = 200
    filter_type_options = ['category', 'status', 'program', 'data_type', 'experimental_strategy', 'reference_genome',
                           'source', 'project_id']
    try:
        settings.pull_metadata()
        filter_dic = settings.bq_table_files['bq_filters']
        if filter_dic:
            file_data = filter_dic['file_data']
            if filter_type:
                if filter_type in file_data:
                    file_data = file_data[filter_type]
                elif filter_type not in filter_type_options:
                    raise ValueError(f"Invalid filter_type - '{filter_type}' is given")
            else:
                raise ValueError(f"No filter_type value was given. filter_type value can be one of the followings: [{', '.joins(filter_type_options)}]")
            options = []
            for op in file_data['options']:
                options.append(op['value'])
            filter_options = {
                "options": options
            }
        response_obj = filter_options
    except ValueError as e:
        status = 400
        response_obj = {'message': f"{e}"}
    except Exception as e:
        status = e.response.status_code
        response_obj = {'message': e.response}
    return jsonify(response_obj), status





@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


settings.setup_app(app)
swagger = Swagger(app, template=swagger_config.swagger_template,config=swagger_config.swagger_config)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
