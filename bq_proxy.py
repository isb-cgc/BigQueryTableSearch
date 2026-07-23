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

import csv
import sqlite3
import io
import sys
import settings
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig
import logging

logger = logging.getLogger(__name__)

#
# Create an in-memory database table with contents of BQ table
#

def _load_bq_table(client, use_conn, pull_query, create_query, insert_query):
  cursor1 = use_conn.cursor()

  # Load table from BQ into in-memory file:
  query_job = client.query(pull_query)

  file_obj = io.StringIO()

  writer = csv.writer(file_obj)
  for row in query_job:
      writer.writerow(row)

  file_obj.seek(0)

  # Create the sqlite table:
  cursor1.execute(create_query)

  # Reading the contents of the in-memory CSV file
  contents = csv.reader(file_obj)

  # Importing the contents of the file
  cursor1.executemany(insert_query, contents)
  use_conn.commit()
  del file_obj
  cursor1.close()
  return

#
# Do a sanity check on the database table
#

def _probe_sql_table(use_conn, select_query):
  cursor2 = use_conn.cursor()
  rows = cursor2.execute(select_query).fetchall()

  # Output to the console screen
  count = 0
  for r in rows:
      if count < 1:
            logger.info(r)
      elif count % 5000 == 0:
        logger.info(count)
      count += 1
  cursor2.close()
  return

def build_the_local_proxy():
  logger.info(f"SQLite Version is: {sqlite3.sqlite_version}")

  refs_table = {
    'bq_query': f'SELECT * FROM `{settings.BQ_METADATA_PROJ}.bqs_metadata.BQS_TABLE_REFS`',
    'table_create': '''CREATE TABLE BQS_TABLE_REFS (
        key_id INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL,
        projectId TEXT,
        datasetId TEXT,
        tableId TEXT,
        friendlyName TEXT,
        description TEXT,
        metadata TEXT);
    ''',
    'insert_records': '''INSERT INTO BQS_TABLE_REFS (id, projectID, 
                        datasetId, tableId, friendlyName, description, metadata) 
                          VALUES(?, ?, ?, ?, ?, ?, ?)''',
    'dump_query': '''SELECT * FROM BQS_TABLE_REFS'''
  }

  schema_table = {
    'bq_query': f'SELECT * FROM `{settings.BQ_METADATA_PROJ}.bqs_metadata.BQS_SCHEMA_FIELDS`',
    'table_create': '''CREATE TABLE BQS_SCHEMA_FIELDS (
        key_id INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL,
        name TEXT);
    ''',
    'insert_records': '''INSERT INTO BQS_SCHEMA_FIELDS (id, name) VALUES(?, ?)''',
    'dump_query': '''SELECT * FROM BQS_SCHEMA_FIELDS'''
  }

  label_table = {
    'bq_query': f'SELECT * FROM `{settings.BQ_METADATA_PROJ}.bqs_metadata.BQS_LABELS`',
    'table_create': '''CREATE TABLE BQS_LABELS (
        key_id INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL,
        labelKey TEXT,
        labelValue TEXT);
    ''',
    'insert_records': '''INSERT INTO BQS_LABELS (id, labelKey, labelValue) VALUES(?, ?, ?)''',
    'dump_query': '''SELECT * FROM BQS_LABELS'''
  }

  db_tables = [refs_table, schema_table, label_table]

  # Create a NAMED in-memory database with shared cache. Note this connection
  # MUST BE KEPT OPEN TO KEEP THE DB IN MEMORY
  hold_until_exit_conn = sqlite3.connect("file:bill_db?mode=memory&cache=shared", uri=True)


  # Connect to the SAME named in-memory database with conn2
  conn = sqlite3.connect("file:bill_db?mode=memory&cache=shared", uri=True)

  # Construct a BigQuery client object.
  client = bigquery.Client()
  # Need to have really big csv field sizes:
  csv.field_size_limit(sys.maxsize)

  for table in db_tables:
    _load_bq_table(client, conn, table['bq_query'], table['table_create'], table['insert_records'])
    da_query = table['bq_query']
    _probe_sql_table(conn, table['dump_query'])
    logger.info(f"done with load: {da_query}")

  # closing the database connection
  conn.close()

  # database disappears (or does it??)
  #hold_until_exit_conn.close()
  return

# with the conditions (list of field-val tuples), build an sql where clause
def query_for_result(settings, parameters, query_statement):
    bigquery_client = bigquery.Client(project=settings.BQ_METADATA_PROJ)

    # Build Query Job Config
    job_config = QueryJobConfig(allow_large_results=True, use_query_cache=False, priority='INTERACTIVE')

    if parameters and len(parameters):
        logger.info("Parameters")
        logger.info(parameters)
        job_config.query_parameters = parameters
        job_config.use_legacy_sql = False

    logger.info("Query")
    logger.info(query_statement)
    query_job = bigquery_client.query(query_statement, job_config=job_config)
    result = query_job.result(timeout=30)
    return result

def list_rows(proj_id, dataset_id, table_id, max_row):
    logger.info(f"{proj_id} {dataset_id} {table_id} {max_row}")
    client = bigquery.Client(project=proj_id)
    rows_iter = client.list_rows(f'{proj_id}.{dataset_id}.{table_id}', max_results=max_row)
    return rows_iter

