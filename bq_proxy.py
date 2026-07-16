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

from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig
import logging

logger = logging.getLogger(__name__)

# with the conditions (list of field-val tuples), build an sql where clause
def query_for_result(settings, parameters, query_statement):
    bigquery_client = bigquery.Client(project=settings.BQ_METADATA_PROJ)

    # Build Query Job Config
    job_config = QueryJobConfig(allow_large_results=True, use_query_cache=False, priority='INTERACTIVE')

    if parameters and len(parameters):
        print("Parameters")
        print(parameters)
        job_config.query_parameters = parameters
        job_config.use_legacy_sql = False

    print("Query")
    print(query_statement)
    query_job = bigquery_client.query(query_statement, job_config=job_config)
    result = query_job.result(timeout=30)
    return result

def list_rows(proj_id, dataset_id, table_id, max_row):
    print(proj_id, dataset_id, table_id, max_row)
    client = bigquery.Client(project=proj_id)
    rows_iter = client.list_rows(f'{proj_id}.{dataset_id}.{table_id}', max_results=max_row)
    return rows_iter

