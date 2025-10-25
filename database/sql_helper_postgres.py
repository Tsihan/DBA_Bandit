import configparser
import copy
import datetime
import logging
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from psycopg2 import sql

import constants
from database.column import Column
from database.table import Table

# -------------------------------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------------------------------

db_config = configparser.ConfigParser()
db_config.read(constants.DB_CONFIG)
db_type = db_config.get('SYSTEM', 'db_type', fallback='POSTGRESQL')
_db_section = db_config[db_type]
database = _db_section.get('database', '')
dataset_name = constants.DATASET_NAME or database.upper()

_table_scan_template_key = dataset_name.upper()
if _table_scan_template_key not in constants.TABLE_SCAN_TIMES:
    logging.warning("Dataset '%s' not found in TABLE_SCAN_TIMES constants; using empty template.",
                    _table_scan_template_key)
    constants.TABLE_SCAN_TIMES[_table_scan_template_key] = defaultdict(list)

table_scan_times_hyp = copy.deepcopy(constants.TABLE_SCAN_TIMES[_table_scan_template_key])
table_scan_times = copy.deepcopy(constants.TABLE_SCAN_TIMES[_table_scan_template_key])

_tables_global: Dict[str, Table] = {}
_pk_columns_dict: Dict[str, List[str]] = {}


# -------------------------------------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------------------------------------


def _qualname(schema: str, name: str) -> str:
    return f"{schema}.{name}"


def _collect_plan_usage(plan_node: Dict, non_clustered_usage: List[Tuple], clustered_usage: List[Tuple]):
    node_type = plan_node.get('Node Type', '')
    relation = plan_node.get('Relation Name') or plan_node.get('Alias')
    actual_time = float(plan_node.get('Actual Total Time', 0.0)) / 1000.0
    plan_rows = float(plan_node.get('Plan Rows', 0.0))
    actual_rows = float(plan_node.get('Actual Rows', plan_rows))
    total_cost = float(plan_node.get('Total Cost', 0.0))

    if node_type in {'Index Scan', 'Index Only Scan'}:
        index_name = plan_node.get('Index Name')
        if index_name:
            non_clustered_usage.append((index_name, actual_time, actual_time, total_cost, actual_rows, plan_rows))
    elif node_type in {'Bitmap Index Scan'}:
        index_name = plan_node.get('Index Name')
        if index_name:
            non_clustered_usage.append((index_name, actual_time, actual_time, total_cost, actual_rows, plan_rows))
    elif node_type in {'Seq Scan', 'Bitmap Heap Scan', 'Tid Scan'}:
        if relation:
            clustered_usage.append((relation, actual_time, actual_time, total_cost, actual_rows, plan_rows))

    for child in plan_node.get('Plans', []) or []:
        _collect_plan_usage(child, non_clustered_usage, clustered_usage)


def merge_index_use(index_uses):
    d = defaultdict(list)
    for index_use in index_uses:
        if index_use[0] not in d:
            d[index_use[0]] = [0] * (len(index_use) - 1)
        d[index_use[0]] = [sum(x) for x in zip(d[index_use[0]], index_use[1:])]
    return [tuple([x] + y) for x, y in d.items()]


def get_selectivity_list(query_obj_list):
    selectivity_list = []
    for query_obj in query_obj_list:
        selectivity_list.append(query_obj.selectivity)
    return selectivity_list


# -------------------------------------------------------------------------------------------------
# Index management
# -------------------------------------------------------------------------------------------------


def create_index_v1(connection, schema_name, tbl_name, col_names, idx_name, include_cols=()):
    column_list = sql.SQL(', ').join(sql.Identifier(col) for col in col_names)
    include_clause = sql.SQL('')
    if include_cols:
        include_clause = sql.SQL(' INCLUDE ({cols})').format(
            cols=sql.SQL(', ').join(sql.Identifier(col) for col in include_cols)
        )
    statement = sql.SQL(
        'CREATE INDEX IF NOT EXISTS {index} ON {table} ({columns}){include_clause}'
    ).format(
        index=sql.Identifier(idx_name),
        table=sql.Identifier(schema_name, tbl_name),
        columns=column_list,
        include_clause=include_clause
    )
    cursor = connection.cursor()
    start = time.perf_counter()
    cursor.execute(statement)
    connection.commit()
    elapsed = time.perf_counter() - start
    logging.info("Added index %s", idx_name)
    return elapsed


def create_index_v2(connection, query):
    start = time.perf_counter()
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    elapsed = time.perf_counter() - start
    return elapsed


def create_statistics(connection, query):
    start_time_execute = datetime.datetime.now()
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    end_time_execute = datetime.datetime.now()
    return (end_time_execute - start_time_execute).total_seconds()


def bulk_create_indexes(connection, schema_name, bandit_arm_list):
    cost = {}
    for index_name, bandit_arm in bandit_arm_list.items():
        cost[index_name] = create_index_v1(connection, schema_name, bandit_arm.table_name,
                                           bandit_arm.index_cols, bandit_arm.index_name,
                                           bandit_arm.include_cols)
        set_arm_size(connection, bandit_arm)
    return cost


def drop_index(connection, schema_name, tbl_name, idx_name):
    statement = sql.SQL('DROP INDEX IF EXISTS {index_name}').format(
        index_name=sql.Identifier(schema_name, idx_name)
    )
    cursor = connection.cursor()
    cursor.execute(statement)
    connection.commit()
    logging.info("Removed index %s", idx_name)


def bulk_drop_index(connection, schema_name, bandit_arm_list):
    for index_name, bandit_arm in bandit_arm_list.items():
        drop_index(connection, schema_name, bandit_arm.table_name, bandit_arm.index_name)


def simple_execute(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()


# -------------------------------------------------------------------------------------------------
# Query execution metrics
# -------------------------------------------------------------------------------------------------


def execute_query_v1(connection, query):
    cleaned_query = query.strip().rstrip(';')
    cursor = connection.cursor()
    cursor.execute('DISCARD ALL;')
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {cleaned_query}"
    try:
        cursor.execute(explain_query)
        plan_result = cursor.fetchone()
    except Exception:
        logging.exception("Exception when executing query: %s", cleaned_query)
        return 0, [], []
    finally:
        cursor.close()

    if not plan_result:
        return 0, [], []

    plan_root = plan_result[0][0]
    total_time_sec = float(plan_root.get('Execution Time', 0.0)) / 1000.0
    non_clustered_usage: List[Tuple] = []
    clustered_usage: List[Tuple] = []
    _collect_plan_usage(plan_root.get('Plan', {}), non_clustered_usage, clustered_usage)
    return total_time_sec, non_clustered_usage, clustered_usage


def create_query_drop_v3(connection, schema_name, bandit_arm_list, arm_list_to_add, arm_list_to_delete, queries):
    bulk_drop_index(connection, schema_name, arm_list_to_delete)
    creation_cost = bulk_create_indexes(connection, schema_name, arm_list_to_add)
    execute_cost = 0
    arm_rewards = {}
    if not _tables_global:
        get_tables(connection)

    for query in queries:
        time_taken, non_clustered_index_usage, clustered_index_usage = execute_query_v1(connection,
                                                                                         query.query_string)
        non_clustered_index_usage = merge_index_use(non_clustered_index_usage)
        clustered_index_usage = merge_index_use(clustered_index_usage)
        execute_cost += time_taken
        logging.info("Query %s cost: %s", query.id, time_taken)

        current_clustered_index_scans = {}
        if clustered_index_usage:
            for index_scan in clustered_index_usage:
                table_name = index_scan[0]
                current_clustered_index_scans[table_name] = index_scan[constants.COST_TYPE_CURRENT_EXECUTION]
                if len(query.table_scan_times[table_name]) < constants.TABLE_SCAN_TIME_LENGTH:
                    query.table_scan_times[table_name].append(index_scan[constants.COST_TYPE_CURRENT_EXECUTION])
                if len(table_scan_times[table_name]) < constants.TABLE_SCAN_TIME_LENGTH:
                    table_scan_times[table_name].append(index_scan[constants.COST_TYPE_CURRENT_EXECUTION])

        if non_clustered_index_usage:
            table_counts = {}
            for index_use in non_clustered_index_usage:
                index_name = index_use[0]
                table_name = bandit_arm_list[index_name].table_name
                table_counts[table_name] = table_counts.get(table_name, 0) + 1

            for index_use in non_clustered_index_usage:
                index_name = index_use[0]
                table_name = bandit_arm_list[index_name].table_name
                if len(query.table_scan_times[table_name]) < constants.TABLE_SCAN_TIME_LENGTH:
                    query.index_scan_times[table_name].append(index_use[constants.COST_TYPE_CURRENT_EXECUTION])
                table_scan_time = query.table_scan_times[table_name]
                if len(table_scan_time) > 0:
                    temp_reward = max(table_scan_time) - index_use[constants.COST_TYPE_CURRENT_EXECUTION]
                    temp_reward = temp_reward / table_counts[table_name]
                elif len(table_scan_times[table_name]) > 0:
                    temp_reward = max(table_scan_times[table_name]) - index_use[constants.COST_TYPE_CURRENT_EXECUTION]
                    temp_reward = temp_reward / table_counts[table_name]
                else:
                    logging.error("Queries without index scan information %s", query.id)
                    raise Exception('Missing index scan information')
                if table_name in current_clustered_index_scans:
                    temp_reward -= current_clustered_index_scans[table_name] / table_counts[table_name]
                if index_name not in arm_rewards:
                    arm_rewards[index_name] = [temp_reward, 0]
                else:
                    arm_rewards[index_name][0] += temp_reward

    for key in creation_cost:
        if key in arm_rewards:
            arm_rewards[key][1] += -1 * creation_cost[key]
        else:
            arm_rewards[key] = [0, -1 * creation_cost[key]]
    logging.info("Index creation cost: %s", sum(creation_cost.values()))
    logging.info("Time taken to run the queries: %s", execute_cost)
    return execute_cost, creation_cost, arm_rewards


# -------------------------------------------------------------------------------------------------
# Schema metadata
# -------------------------------------------------------------------------------------------------


def get_all_columns(connection):
    query = '''SELECT table_name, column_name FROM information_schema.columns
               WHERE table_schema = %s;'''
    columns = defaultdict(list)
    cursor = connection.cursor()
    cursor.execute(query, (constants.SCHEMA_NAME,))
    results = cursor.fetchall()
    for result in results:
        columns[result[0]].append(result[1])
    return columns, len(results)


def get_all_columns_v2(connection):
    columns = defaultdict(list)
    cursor = connection.cursor()
    cursor.execute('''SELECT table_name, column_name FROM information_schema.columns
                      WHERE table_schema = %s;''', (constants.SCHEMA_NAME,))
    results = cursor.fetchall()
    count = 0
    for result in results:
        row_count = get_table_row_count(connection, constants.SCHEMA_NAME, result[0])
        if row_count >= constants.SMALL_TABLE_IGNORE:
            columns[result[0]].append(result[1])
            count += 1
    return columns, count


def get_table_row_count(connection, schema_name, tbl_name):
    cursor = connection.cursor()
    cursor.execute('''SELECT reltuples::bigint
                      FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                      WHERE n.nspname = %s AND c.relname = %s;''', (schema_name, tbl_name))
    result = cursor.fetchone()
    if result and result[0] is not None:
        return int(result[0])
    cursor.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(schema_name, tbl_name)))
    return cursor.fetchone()[0]


def get_primary_key(connection, schema_name, table_name):
    if table_name in _pk_columns_dict:
        return _pk_columns_dict[table_name]
    query = '''SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name
               WHERE tc.constraint_type = 'PRIMARY KEY'
                 AND tc.table_schema = %s
                 AND tc.table_name = %s
               ORDER BY kcu.ordinal_position;'''
    cursor = connection.cursor()
    cursor.execute(query, (schema_name, table_name))
    results = cursor.fetchall()
    pk_columns = [row[0] for row in results]
    _pk_columns_dict[table_name] = pk_columns
    return pk_columns


def get_columns(connection, table_name):
    columns: Dict[str, Column] = {}
    cursor = connection.cursor()
    cursor.execute('''SELECT column_name, data_type, character_maximum_length,
                             numeric_precision, datetime_precision
                      FROM information_schema.columns
                      WHERE table_schema = %s AND table_name = %s;''',
                   (constants.SCHEMA_NAME, table_name))
    results = cursor.fetchall()
    for column_name, data_type, char_len, numeric_precision, datetime_precision in results:
        column = Column(table_name, column_name, data_type)
        if char_len is not None:
            column_length = int(char_len)
        elif numeric_precision is not None:
            column_length = int(numeric_precision) // 8
        elif datetime_precision is not None:
            column_length = 8
        else:
            column_length = 8
        column.set_column_size(column_length)
        column.set_max_column_size(column_length)
        columns[column_name] = column
    return columns


def get_tables(connection):
    global _tables_global
    if _tables_global:
        return _tables_global

    tables = {}
    cursor = connection.cursor()
    cursor.execute('''SELECT table_name
                      FROM information_schema.tables
                      WHERE table_schema = %s AND table_type = 'BASE TABLE';''',
                   (constants.SCHEMA_NAME,))
    results = cursor.fetchall()
    for result in results:
        table_name = result[0]
        row_count = get_table_row_count(connection, constants.SCHEMA_NAME, table_name)
        pk_columns = get_primary_key(connection, constants.SCHEMA_NAME, table_name)
        tables[table_name] = Table(table_name, row_count, pk_columns)
        tables[table_name].set_columns(get_columns(connection, table_name))
    _tables_global = tables
    return _tables_global


def get_column_data_length_v2(connection, table_name, col_names):
    tables = get_tables(connection)
    column_data_length = 0
    for column_name in col_names:
        column = tables[table_name].columns[column_name]
        column_data_length += column.column_size if column.column_size else 0
    return column_data_length


def get_max_column_data_length_v2(connection, table_name, col_names):
    tables = get_tables(connection)
    column_data_length = 0
    for column_name in col_names:
        column = tables[table_name].columns[column_name]
        column_data_length += column.max_column_size if column.max_column_size else 0
    return column_data_length


def get_estimated_size_of_index_v1(connection, schema_name, tbl_name, col_names):
    table = get_tables(connection)[tbl_name]
    header_size = 6
    nullable_buffer = 2
    primary_key = get_primary_key(connection, schema_name, tbl_name)
    primary_key_size = get_column_data_length_v2(connection, tbl_name, primary_key)
    col_not_pk = tuple(set(col_names) - set(primary_key))
    key_columns_length = get_column_data_length_v2(connection, tbl_name, col_not_pk)
    index_row_length = header_size + primary_key_size + key_columns_length + nullable_buffer
    row_count = max(table.table_row_count, 1)
    estimated_size = row_count * index_row_length
    estimated_size = estimated_size / float(1024 * 1024)
    max_column_length = get_max_column_data_length_v2(connection, tbl_name, col_names)
    if max_column_length > 1700:
        logging.warning('Index exceeding 1700 bytes: %s', col_names)
        estimated_size = 99999999
    logging.debug('%s : %s', col_names, estimated_size)
    return estimated_size


# -------------------------------------------------------------------------------------------------
# Statistics helpers
# -------------------------------------------------------------------------------------------------


def get_table_scan_times(connection, query_string):
    query_table_scan_times = copy.deepcopy(constants.TABLE_SCAN_TIMES[_table_scan_template_key])
    time_taken, _, clustered_index_scans = execute_query_v1(connection, query_string)
    if clustered_index_scans:
        for index_scan in clustered_index_scans:
            table_name = index_scan[0]
            if len(query_table_scan_times[table_name]) < constants.TABLE_SCAN_TIME_LENGTH:
                query_table_scan_times[table_name].append(index_scan[constants.COST_TYPE_CURRENT_EXECUTION])
    return query_table_scan_times


def get_table_scan_times_structure():
    return copy.deepcopy(constants.TABLE_SCAN_TIMES[_table_scan_template_key])


def get_current_pds_size(connection):
    cursor = connection.cursor()
    cursor.execute('''SELECT COALESCE(SUM(pg_relation_size(indexrelid)), 0)
                      FROM pg_index idx
                      JOIN pg_class c ON c.oid = idx.indexrelid
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                      WHERE n.nspname = %s;''', (constants.SCHEMA_NAME,))
    result = cursor.fetchone()
    return float(result[0]) / (1024 * 1024) if result and result[0] else 0.0


def set_arm_size(connection, bandit_arm):
    cursor = connection.cursor()
    cursor.execute(
        'SELECT pg_relation_size(to_regclass(%s)) / 1024.0 / 1024.0',
        (_qualname(bandit_arm.schema_name, bandit_arm.index_name),)
    )
    result = cursor.fetchone()
    if result and result[0] is not None:
        bandit_arm.memory = float(result[0])
    return bandit_arm


def restart_sql_server():
    logging.info('Skipping database restart for PostgreSQL (not required).')


def get_database_size(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT pg_database_size(current_database()) / 1024.0 / 1024.0;')
    result = cursor.fetchone()
    return float(result[0]) if result and result[0] else 0.0


# -------------------------------------------------------------------------------------------------
# Hypothetical index placeholders (not supported)
# -------------------------------------------------------------------------------------------------


def hyp_create_index_v1(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def hyp_bulk_create_indexes(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def hyp_enable_index(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def hyp_execute_query(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def hyp_create_query_drop_v1(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def hyp_create_query_drop_v2(*args, **kwargs):
    raise NotImplementedError('Hypothetical indexes are not supported for PostgreSQL. Set hyp_rounds = 0.')


def get_query_plan(*args, **kwargs):
    raise NotImplementedError('EXPLAIN XML style plans are not implemented for PostgreSQL helper.')


def get_selectivity_v3(connection, query, predicates):
    cleaned_query = query.strip().rstrip(';')
    cursor = connection.cursor()
    explain_query = f"EXPLAIN (FORMAT JSON) {cleaned_query}"
    cursor.execute(explain_query)
    plan_result = cursor.fetchone()
    cursor.close()
    if not plan_result:
        return {table: 1 for table in predicates.keys()}

    plan_root = plan_result[0][0]
    estimated_rows_per_table: Dict[str, float] = defaultdict(lambda: float('inf'))

    def _collect_selectivity(node):
        node_type = node.get('Node Type', '')
        relation = node.get('Relation Name') or node.get('Alias')
        plan_rows = float(node.get('Plan Rows', 0.0))
        if relation and relation in predicates:
            estimated_rows_per_table[relation] = min(estimated_rows_per_table[relation], plan_rows)
        for child in node.get('Plans', []) or []:
            _collect_selectivity(child)

    _collect_selectivity(plan_root.get('Plan', {}))

    selectivity = {}
    for table in predicates.keys():
        estimated_rows = estimated_rows_per_table[table]
        if estimated_rows == float('inf'):
            selectivity[table] = 1
        else:
            row_count = get_table_row_count(connection, constants.SCHEMA_NAME, table)
            selectivity[table] = min(1, estimated_rows / max(row_count, 1))
    return selectivity


def remove_all_non_clustered(connection, schema_name):
    cursor = connection.cursor()
    cursor.execute('''SELECT indexname
                      FROM pg_indexes
                      WHERE schemaname = %s
                        AND indexname NOT LIKE '%_pkey';''', (schema_name,))
    for row in cursor.fetchall():
        cursor.execute(sql.SQL('DROP INDEX IF EXISTS {}').format(sql.Identifier(schema_name, row[0])))
    connection.commit()


def drop_all_dta_statistics(connection):
    logging.info('Skipping DTA statistics cleanup for PostgreSQL (not applicable).')


def drop_statistic(connection, table_name, stat_name):
    logging.info('Skipping DROP STATISTICS for PostgreSQL (not applicable).')