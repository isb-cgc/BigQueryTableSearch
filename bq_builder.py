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

import re
import settings
from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter, StructQueryParameter
import logging

logger = logging.getLogger(__name__)

# with the conditions (list of field-val tuples), build an sql where clause
def build_where_clause(conditions):
    where_clause = ''
    params = []
    clauses = []
    i = 0
    for k, vals in conditions:
        if i:
            and_or_where = 'AND'
        else:
            and_or_where = 'WHERE'
        param_name = f'{k}_param_{i}'
        param_type = (
            'STRING' if (
                    type(vals) not in [int, float, complex] and re.compile(r'[^0-9\.,]',
                                                                                 re.UNICODE | re.IGNORECASE).search(
                vals)
            ) else 'NUMERIC'
        )
        if k == 'include_always_newest':
            if vals == 'false':
                clauses.append("(NOT ENDS_WITH(LOWER(R.tableId), '_current'))")
                where_clause += f'{and_or_where} NOT ENDS_WITH(LOWER(R.tableId), \'_current\')\n'
                i += 1
        else:
            where_clause += f'{and_or_where} LOWER(R.{k}) '
            if is_quoted(vals) and k not in ['description', 'friendlyName'] or k == 'projectId':
                vals = vals.strip('\'\"')
                params.append(ScalarQueryParameter(param_name, param_type, vals.lower()))
                clauses.append(f'(LOWER(R.{k}) = @{param_name})')
                where_clause += f'= \'{vals.lower()}\'\n'
            else:
                vals = vals.strip('\'\"')
                params.append(ScalarQueryParameter(param_name, param_type, f'%{vals.lower()}%'))
                clauses.append(f'(LOWER(R.{k}) LIKE @{param_name})')
                where_clause += f'LIKE \'%{vals.lower()}%\'\n'
            i += 1

    return where_clause, params, " AND ".join(clauses)


# return true if val is valid and false if invalid character is detected
def is_valid(val):
    invalid_match = re.match('[^a-zA-Z\d\s.\-|_:\'\"]', val.strip('\'\"'))
    return not invalid_match


# return a compiled list of paired field-value tuples from the request
def get_conditions(rq_data, filters):
    conditions = []
    for f in filters:
        val = rq_data.get(f, [])
        if isinstance(val, list):
            v_list = val
        else:
            v_list = val.split('|')
        for v in v_list:
            if v and not is_valid(v):
                raise ValueError
        if len(v_list):
            conditions.append((f, '|'.join(v_list)))
    return conditions


# join sql clause builder
def build_join_clause(conditions, table_name):
    clauses = []
    params = []
    JOIN_BASE = """
        JOIN `{project}.bqs_metadata.{table_name}` AS {table_shorthand}
        ON {table_shorthand}.id = R.id AND (
            {sub_clause}
        )
    """
    join_clause = ''
    SUBCLAUSE_JOIN = """
            OR """
    for k, vals in conditions:
        join_clause += f'JOIN `{settings.BQ_METADATA_PROJ}.bqs_metadata.{table_name}` AS {k}\n'
        join_clause += f'ON {k}.id = R.id\n'
        join_clause += 'AND ( \n'
        i = 0
        sub_clauses = []
        for val in vals.split('|'):
            param_type = (
                'STRING' if (
                        type(vals) not in [int, float, complex] and re.compile(r'[^0-9\.,]',
                                                                               re.UNICODE | re.IGNORECASE).search(
                    vals)
                ) else 'NUMERIC'
            )
            param_name = f'{k}_param_{i}'
            if i > 0:
                join_clause += ' OR '
            if k in ['field_name', 'labels']:
                field = 'name' if k == 'field_name' else 'labelValue'
                sub_clauses.append(f'(LOWER({k}.{field}) LIKE @{param_name})')
                join_clause += f'(LOWER({k}.{field}) LIKE \'%{val.lower()}%\')\n'
                params.append(ScalarQueryParameter(param_name, param_type, f'%{val.lower()}%'))
            else:
                labelKey_param_name = f'lk_{k}_param_{i}'
                params.append(ScalarQueryParameter(labelKey_param_name, 'STRING', f'{k}'))
                sub_clauses.append(f'({k}.labelKey = @{labelKey_param_name} AND {k}.labelValue = @{param_name})')
                params.append(ScalarQueryParameter(param_name, param_type, val.lower()))
                join_clause += f'({k}.labelKey = \'{k}\' AND {k}.labelValue = \'{val}\')\n'
            i += 1
        clauses.append(
            JOIN_BASE.format(
                project=settings.BQ_METADATA_PROJ,
                table_name=table_name,
                table_shorthand=k,
                sub_clause=SUBCLAUSE_JOIN.join(sub_clauses)
            )
        )
        join_clause += (')\n')

    return join_clause, params, "\n".join(clauses)


# return an SQL query statement with the given search criteria in req
def metadata_query(req):
    req_data = None
    if req.method == 'POST':
        if req.form:
            req_data = req.form.to_dict(flat=False)
        if req.is_json:
            req_data = req.get_json()
    else:
        req_data = req.args.to_dict(flat=False)
    r_filters = ['description', 'friendlyName', 'projectId', 'datasetId', 'tableId', 'include_always_newest']
    l_filters = ['status', 'category', 'experimental_strategy', 'data_type', 'source', 'program', 'reference_genome',
                 'labels']
    f_filters = ['field_name']
    parameters = []
    where_clause, params, where_clause_param = build_where_clause(get_conditions(req_data, r_filters))
    parameters.extend(params)
    join_clause, params, join_clause_labels = build_join_clause(get_conditions(req_data, l_filters), 'BQS_LABELS')
    parameters.extend(params)
    join_clause_f, params, join_clause_schema = build_join_clause(get_conditions(req_data, f_filters), 'BQS_SCHEMA_FIELDS')
    parameters.extend(params)
    join_clause += join_clause_f

    QUERY_BASE = """
        SELECT distinct metadata 
        FROM `{project_id}.bqs_metadata.BQS_TABLE_REFS` AS R
        {join_clause_labels}
        {join_clause_schema}
        {where_clause}
    """

    query_str = QUERY_BASE.format(
        project_id=settings.BQ_METADATA_PROJ,
        join_clause_labels=join_clause_labels if len(join_clause_labels) else '',
        join_clause_schema=join_clause_schema if len(join_clause_schema) else '',
        where_clause="WHERE {}".format(where_clause_param) if where_clause_param else ''
    )

    query_str_old = f'SELECT distinct metadata FROM `{settings.BQ_METADATA_PROJ}.bqs_metadata.BQS_TABLE_REFS` AS R \n'
    query_str_old += join_clause
    query_str_old += where_clause

    logger.info("DYNAMIC VERSION:\n {}".format(query_str_old))
    logger.info("PARAMETERIZED VERSION: {}".format(query_str))


    return query_str, parameters


# returns true if the field_val is wrapped with single quotes or double quotes
def is_quoted(field_val):
    if field_val:
        single_quotes = re.fullmatch(r"^\'.*\'$", field_val)
        double_quotes = re.fullmatch(r'^\".*\"$', field_val)
        return single_quotes or double_quotes
    else:
        return False
