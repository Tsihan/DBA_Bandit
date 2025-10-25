#!/usr/bin/env python3
"""
Script to convert JOB benchmark queries to DBABandits workload format.
This reads all .sql files from the JOB queries directory and creates a JSON workload file.
"""

import json
import os
import glob
import re

# Path to JOB queries directory
JOB_QUERIES_DIR = "/home/qihan/load_imdb/job_queries"
OUTPUT_FILE = "resources/workloads/job_all_queries.json"

def extract_tables_from_query(query):
    """Extract table names from SQL query."""
    # Pattern to match table names in FROM and JOIN clauses
    # This handles: FROM table AS alias, JOIN table AS alias
    pattern = r'(?:FROM|JOIN)\s+(\w+)\s+AS'
    tables = re.findall(pattern, query, re.IGNORECASE)
    return list(set(tables))  # Remove duplicates

def extract_predicates(query, tables):
    """
    Simple predicate extraction based on WHERE clause columns.
    Returns a dict mapping table names to lists of columns used in predicates.
    """
    predicates = {}
    
    # Extract WHERE clause
    where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|;|$)', query, re.IGNORECASE | re.DOTALL)
    if not where_match:
        return predicates
    
    where_clause = where_match.group(1)
    
    # Find all table.column or alias.column references
    for table in tables:
        # Look for patterns like "table.column" or "alias.column" in WHERE clause
        pattern = rf'\b{table[0]}\.(\w+)'
        columns = re.findall(pattern, where_clause)
        if columns:
            predicates[table] = list(set(columns))
    
    return predicates

def extract_payload(query, tables):
    """
    Extract payload (columns accessed) from query.
    For simplicity, we'll just include common columns that might be accessed.
    """
    payload = {}
    
    # Extract SELECT clause
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return payload
    
    select_clause = select_match.group(1)
    
    # For each table, try to find columns referenced
    for table in tables:
        pattern = rf'\b{table[0]}\.(\w+)'
        columns = re.findall(pattern, select_clause)
        if columns:
            payload[table] = list(set(columns))
    
    # Also check in WHERE clause for join conditions
    where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|;|$)', query, re.IGNORECASE | re.DOTALL)
    if where_match:
        where_clause = where_match.group(1)
        for table in tables:
            pattern = rf'\b{table[0]}\.(\w+)'
            columns = re.findall(pattern, where_clause)
            if columns:
                if table not in payload:
                    payload[table] = []
                payload[table].extend(columns)
                payload[table] = list(set(payload[table]))
    
    return payload

def process_job_queries():
    """Process all JOB query files and generate workload JSON."""
    workload_entries = []
    
    # Get all .sql files
    sql_files = sorted(glob.glob(os.path.join(JOB_QUERIES_DIR, "*.sql")))
    
    print(f"Found {len(sql_files)} JOB query files")
    
    for idx, sql_file in enumerate(sql_files, start=1):
        with open(sql_file, 'r') as f:
            query = f.read().strip()
        
        # Clean up the query - normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Extract metadata
        tables = extract_tables_from_query(query)
        predicates = extract_predicates(query, tables)
        payload = extract_payload(query, tables)
        
        entry = {
            "id": idx,
            "query_string": query,
            "predicates": predicates,
            "payload": payload,
            "group_by": {},
            "order_by": {}
        }
        
        workload_entries.append(entry)
        
        if idx <= 5:  # Print first 5 for verification
            print(f"\nQuery {idx} ({os.path.basename(sql_file)}):")
            print(f"  Tables: {tables}")
            print(f"  Predicates: {predicates}")
    
    # Write to output file
    output_path = os.path.join("/home/qihan/DBABandits", OUTPUT_FILE)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        for entry in workload_entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"\n✅ Successfully created workload file: {output_path}")
    print(f"   Total queries: {len(workload_entries)}")
    
    return len(workload_entries)

if __name__ == "__main__":
    num_queries = process_job_queries()
    print(f"\nYou can now run the experiment with all {num_queries} JOB queries!")
    print("Don't forget to update exp.conf with appropriate rounds and query ranges.")
