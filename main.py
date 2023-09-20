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
from flask import Flask, render_template, request, send_from_directory, jsonify, json, make_response, abort
from flask_talisman import Talisman
import requests
import logging
from google.cloud import bigquery
# , storage, exceptions
from oauth2client.client import GoogleCredentials

# from oauth2client.client import flow_from_clientsecrets, GoogleCredentials

logger = logging.getLogger('main_logger')

app = Flask(__name__)

TIER = os.environ.get('TIER', 'test')
app.config['TESTING'] = (TIER.lower() != 'prod')
app.config['ENV'] = 'production' if TIER.lower() == 'prod' else 'development'

MAX_RESULT_SIZE = 50000

# length of time (in seconds) the browser will respect the HSTS header
# production and UAT should be set to 31,536,000 seconds (by not setting any HSTS_MAX_age,
# else set to 3600 (test and dev)
hsts_max_age = int(os.environ.get('HSTS_MAX_AGE') or 3600)

# length of time (in seconds) the browser will respect the HSTS header
# hsts_max_age = 31536000 if TIER.lower() == 'prod' or  TIER.lower() == 'uat' else 3600

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

BQ_ECOSYS_BUCKET = os.environ.get('BQ_ECOSYS_BUCKET',
                                  'https://storage.googleapis.com/webapp-static-files-isb-cgc-dev/bq_ecosys/')

@app.route("/privacy/")
def privacy():
    return render_template("privacy.html")

@app.route("/bq_meta_data/<proj_id>.<dataset_id>.<table_id>/", methods=['GET', 'POST'])
@app.route("/", methods=['GET', 'POST'])
def home(proj_id=None, dataset_id=None, table_id=None):
    bq_filter_file_name = 'bq_meta_filters.json'
    bq_filter_file_path = BQ_ECOSYS_BUCKET + bq_filter_file_name
    bq_filters = requests.get(bq_filter_file_path).json()
    # bq_filters['selected_table_full_id'] = table_id
    bq_filters['selected_table_full_id'] = f'{proj_id}.{dataset_id}.{table_id}'
    selected_filters_list = []
    if request.method == 'POST':
        rq_meth = request.form
    else:
        rq_meth = request.args

    filter_list = ['projectId', 'datasetId', 'tableId', 'friendlyName', 'description', 'field_name', 'labels', 'access',
                   'status', 'category', 'experimental_strategy', 'program', 'source', 'data_type',
                   'reference_genome']
    for f in filter_list:
        if rq_meth.get(f):
            selected_filters_list.append('{filter}={value}'.format(filter=f, value=rq_meth.get(f)))
    print('selected_filters_list')
    print(selected_filters_list)
    bq_filters['selected_filters'] = '&'.join(selected_filters_list)
    return render_template("bq_meta_search.html", bq_filters=bq_filters)


def filter_by_prop(rq_meth, rows, attr_list, sub_category, is_exact_match):
    for attr in attr_list:
        f_val = rq_meth.get(attr, '').strip().lower()

        if f_val:
            filtered_rows = []
            for row in rows:
                add_row = False
                if sub_category:
                    field_dict = row.get(sub_category)
                    if field_dict:
                        if sub_category == 'labels':
                            for k in field_dict.keys():
                                if k.startswith(attr) and field_dict.get(k).lower() == f_val:
                                    add_row = True
                                    break
                        else:
                            if field_dict.get(attr).lower() == f_val:
                                add_row = True
                else:
                    if is_exact_match:
                        if row.get(attr).lower() == f_val:
                            add_row = True
                    else:
                        if row.get(attr) and f_val in row.get(attr).lower():
                            add_row = True
                if add_row:
                    filtered_rows.append(row)
            rows = filtered_rows
    return rows


def filter_by_field_name(rq_meth, rows):
    f_val = rq_meth.get('field_name', '').strip().lower()
    print(f_val)
    if f_val:
        filtered_rows = []
        for row in rows:
            field_dict = row.get('schema')
            if field_dict:
                field_list = field_dict.get('fields')
                for field in field_list:
                    if field['name'].lower() == f_val:
                        filtered_rows.append(row)
                        break
        rows = filtered_rows
    return rows


def filter_by_all_labels(rq_meth, rows):
    f_val = rq_meth.get('labels', '').strip().lower()
    print('f_val')
    print(f_val)
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
    tbl_ref_filters = ['projectId', 'datasetId', 'tableId']
    label_filters = ['access', 'status', 'category', 'experimental_strategy', 'data_type', 'source', 'program',
                     'reference_genome']

    filter_prop_list = [{'attr_list': generic_filters, 'subcategory': None, 'is_exact_match': False},
                        {'attr_list': tbl_ref_filters, 'subcategory': 'tableReference', 'is_exact_match': True},
                        {'attr_list': label_filters, 'subcategory': 'labels', 'is_exact_match': True}]
    for filter_prop in filter_prop_list:
        rows = filter_by_prop(rq_meth, rows, filter_prop['attr_list'], filter_prop['subcategory'],
                              filter_prop['is_exact_match'])
    rows = filter_by_field_name(rq_meth, rows)
    rows = filter_by_all_labels(rq_meth, rows)

    return rows


@app.route("/bq_meta_data", methods=['GET', 'POST'])
def bq_meta_data():
    bq_meta_data_file_name = 'bq_meta_data.json'
    bq_meta_data_file_path = BQ_ECOSYS_BUCKET + bq_meta_data_file_name
    bqt_meta_data = filter_rows(requests.get(bq_meta_data_file_path).json(), request)
    bq_useful_join_file_name = 'bq_useful_join.json'
    bq_useful_join_file_path = BQ_ECOSYS_BUCKET + bq_useful_join_file_name
    bq_useful_join = requests.get(bq_useful_join_file_path).json()
    for bq_meta_data_row in bqt_meta_data:
        useful_joins = []
        row_id = bq_meta_data_row['id']
        for join in bq_useful_join:
            if join['id'] == row_id:
                useful_joins = join['joins']
                break
        bq_meta_data_row['usefulJoins'] = useful_joins
    return jsonify(bqt_meta_data)


def get_nested_data(row_cell):
    nested_cell_data_dict = {}
    for sub_row in row_cell:
        for sub_key in sub_row.keys():
            if type(sub_row[sub_key]) is list:
                # double_nested_cell_data_dict = {}
                for double_sub_row in sub_row[sub_key]:
                    for double_sub_key in double_sub_row.keys():
                        if nested_cell_data_dict.get(f'{sub_key}.{double_sub_key}'):
                            nested_cell_data_dict[f'{sub_key}.{double_sub_key}'].append(f'{sub_key}.{double_sub_key}:{double_sub_row[double_sub_key]}')
                        else:
                            nested_cell_data_dict[f'{sub_key}.{double_sub_key}'] = [f'{sub_key}.{double_sub_key}:{double_sub_row[double_sub_key]}']
                            # nested_cell_data_dict[double_sub_key] = [double_sub_row[double_sub_key]]
                # print(sub_row[sub_key])
                # return get_nested_data(sub_row[sub_key])
            else:
                if nested_cell_data_dict.get(sub_key):
                    nested_cell_data_dict[sub_key].append(f'single-{sub_key}:{sub_row[sub_key]}')
                    # nested_cell_data_dict[sub_key].append(sub_row[sub_key])

                else:
                    nested_cell_data_dict[sub_key] = [f'single-{sub_key}:{sub_row[sub_key]}']
                # nested_cell_data_dict[sub_key] = [sub_row[sub_key]]
    return nested_cell_data_dict


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



@app.route("/get_tbl_preview/<proj_id>/<dataset_id>/<table_id>/", methods=['GET', 'POST'])
def get_tbl_preview(proj_id, dataset_id, table_id):
    status = 200
    MAX_ROW = 8
    try:
        if not proj_id or not dataset_id or not table_id:
            logger.warning("[WARNING] Required ID missing: {}.{}.{}".format(proj_id, dataset_id, table_id))
            status = 503
            result = {
                'message': "There was an error while processing this request: one or more required parameters (project id, dataset_id or table_id) were not supplied."
            }
        else:
            client = bigquery.Client(project=proj_id)
            rows_iter = client.list_rows(f'{proj_id}.{dataset_id}.{table_id}', max_results=8)
            # table_data = []
            # column_names_dic = []
            if rows_iter and rows_iter.total_rows:
                schema_fields = [schema.to_api_repr() for schema in list(rows_iter.schema)]

                # for sf in schema_fields:
                #     if sf.fields:
                #         for sub_field in sf.fields:
                #             if sub_field.fields:
                #                 for double_sub_field in sub_field.fields:
                #                     column_names.append(f'{sf.name}.{sub_field.name}.{double_sub_field.name}')
                #             else:
                #                 column_names.append(f'{sf.name}.{sub_field.name}')
                #     else:
                #         column_names.append(sf.name)
                tbl_data = [dict(row) for row in list(rows_iter)]
                # print(list(rows[0].values()))

                # for row in rows:
                #     row_data = []
                #     for column_name in row.keys():
                #         row_cell = row.get(column_name)
                #         # print(column_name)
                #         if type(row_cell) is list:
                #             nested_cell_data_dict = get_nested_data(row_cell)
                #
                #             # nested_cell_data_dict = {}
                #             # for sub_row in row_cell:
                #             #     for sub_key in sub_row.keys():
                #             #         if nested_cell_data_dict.get(sub_key):
                #             #             nested_cell_data_dict[sub_key].append(sub_row[sub_key])
                #             #         else:
                #             #             nested_cell_data_dict[sub_key] = [sub_row[sub_key]]
                #             row_data.append(list(nested_cell_data_dict.values()))
                #         else:
                #             row_data.append(row_cell)
                #
                #     table_data.append(row_data)

                # print(rows_iter.first_page_response)
                # if len(rows) > 0:
                # print(table_rows[0])
                result = {
                    'tbl_data': tbl_data,
                    # 'table_data': table_data,
                    'schema_fields': schema_fields
                    # 'column_names_dic': column_names_dic
                }

            else:
                result = {
                    'message': 'No record has been found for table {proj_id}.{dataset_id}.{table_id}.'.format(
                        proj_id=proj_id,
                        dataset_id=dataset_id,
                        table_id=table_id)
                }

            # bq_service = get_bigquery_service()
            # dataset = bq_service.datasets().get(projectId=proj_id, datasetId=dataset_id).execute()
            # is_public = False
            # for access_entry in dataset['access']:
            #     if access_entry.get('role') == 'READER' and access_entry.get('specialGroup') == 'allAuthenticatedUsers':
            #         is_public = True
            #         break
            # if is_public:
            #     tbl_data=bq_service.tables().get(projectId=proj_id, datasetId=dataset_id, tableId=table_id).execute()
            #     if tbl_data.get('type') == 'VIEW' and tbl_data.get('view') and tbl_data.get('view').get('query'):
            #         view_query_template = '''#standardSql
            #                 {query_stmt}
            #                 LIMIT {max}'''
            #         view_query = view_query_template.format(query_stmt=tbl_data['view']['query'], max=MAX_ROW)
            #         response = bq_service.jobs().query(
            #             projectId=settings.BIGQUERY_PROJECT_ID,
            #             body={ 'query': view_query  }).execute()
            #     else:
            #         response = bq_service.tabledata().list(projectId=proj_id, datasetId=dataset_id, tableId=table_id,
            #                                            maxResults=MAX_ROW).execute()
            #     if response and int(response['totalRows']) > 0:
            #         result = {
            #             'rows': response['rows']
            #         }
            #     else:
            #         result = {
            #             'message': 'No record has been found for table {proj_id}.{dataset_id}.{table_id}.'.format(
            #                 proj_id=proj_id,
            #                 dataset_id=dataset_id,
            #                 table_id=table_id)
            #         }
            # else:
            #     status = 401
            #     result = {
            #         'message': "Preview is not available for this table/view."
            #     }

    except ValueError as e:
        logger.error(
            "[ERROR] While attempting to retrieve preview data for {proj_id}.{dataset_id}.{table_id} table:".format(
                proj_id=proj_id,
                dataset_id=dataset_id,
                table_id=table_id))
        logger.exception(e)
        status = 500
        result = {
            'message': "There was an error while processing this request."
        }
        # if status == 403:
        #     result = {
        #         'message': "Your attempt to preview this table [{proj_id}.{dataset_id}.{table_id}] was denied.".format(
        #             proj_id=proj_id,
        #             dataset_id=dataset_id,
        #             table_id=table_id)
        #     }

    except Exception as e:
        status = 503
        result = {
            'message': "There was an error while processing this request."
        }
        logger.error(
            "[ERROR] While attempting to retrieve preview data for {proj_id}.{dataset_id}.{table_id} table:".format(
                proj_id=proj_id,
                dataset_id=dataset_id,
                table_id=table_id))
        logger.exception(e)

    return jsonify(result)



# @app.route('/_ah/warmup')
# def warmup():
#     # Handle your warmup logic here, e.g. set up a database connection pool
#     return '', 200, {}

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
