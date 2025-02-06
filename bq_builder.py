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


def build_where_clause(conditions):
    where_clause = ''
    i = 0
    for k, vals in conditions:
        if i:
            and_or_where = 'AND'
        else:
            and_or_where = 'WHERE'
        if k == 'include_always_newest':
            if vals == 'false':
                where_clause += f'{and_or_where} NOT ENDS_WITH(LOWER(R.tableId), \'_current\')\n'
                i += 1
        else:
            where_clause += f'{and_or_where} LOWER(R.{k}) '
            if is_quoted(vals) and k not in ['description', 'friendlyName'] or k == 'projectId':
                where_clause += f'= {vals.lower()}\n'
            else:
                vals = vals.strip('\'\"')
                where_clause += f'LIKE \'%{vals.lower()}%\'\n'
            i += 1
    return where_clause


def is_valid(val):
    invalid_match = re.match('[^a-zA-Z\d\s.-_:\'\"]', val.strip('\'\"'))
    return not invalid_match


def get_conditions(rq_meth, filters):
    conditions = []
    for f in filters:
        v = rq_meth.get(f, None)
        if v and is_valid(v):
            conditions.append((f, v))
    return conditions


def build_join_clause(conditions, table_name):
    join_clause = ''
    for k, vals in conditions:
        join_clause += f'JOIN `{settings.BQ_METADATA_PROJ}.bqs_metadata.{table_name}` AS {k}\n'
        join_clause += f'ON {k}.id = R.id\n'
        join_clause += 'AND ( \n'
        i = 0
        for val in vals.split('|'):
            if i:
                join_clause += 'OR '
            if k == 'field_name':
                join_clause += f'(LOWER({k}.name) LIKE (\'%{val.lower()}%\')\n'
            elif k == 'labels':
                join_clause += f'(LOWER({k}.labelValue) LIKE \'%{val.lower()}%\')\n'
            else:
                join_clause += f'({k}.labelKey = \'{k}\' AND {k}.labelValue = \'{val}\')\n'
            i += 1
        join_clause += (')\n')
    return join_clause


def metadata_query(req):
    if req.method == 'POST':
        rq_meth = req.form
    else:
        rq_meth = req.args
    r_filters = ['description', 'friendlyName', 'projectId', 'datasetId', 'tableId', 'include_always_newest']
    l_filters = ['status', 'category', 'experimental_strategy', 'data_type', 'source', 'program', 'reference_genome',
                 'labels']
    f_filters = ['field_name']
    where_clause = build_where_clause(get_conditions(rq_meth, r_filters))
    join_clause = build_join_clause(get_conditions(rq_meth, l_filters), 'BQS_LABELS')
    join_clause += build_join_clause(get_conditions(rq_meth, f_filters), 'BQS_SCHEMA_FIELDS')
    query_str = f'SELECT metadata FROM `{settings.BQ_METADATA_PROJ}.bqs_metadata.BQS_TABLE_REFS` AS R \n'
    query_str += join_clause
    query_str += where_clause
    return query_str


def is_quoted(field_val):
    if field_val:
        single_quotes = re.fullmatch(r"^\'.*\'$", field_val)
        double_quotes = re.fullmatch(r'^\".*\"$', field_val)
        return single_quotes or double_quotes
    else:
        return False
