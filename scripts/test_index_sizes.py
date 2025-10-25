#!/usr/bin/env python3
"""
Test script to check which indexes will fail due to size limits.
This helps identify problematic column combinations before running the full experiment.
"""

import psycopg2
import configparser

def test_index_creation():
    config = configparser.ConfigParser()
    config.read('config/db.conf')
    
    conn = psycopg2.connect(
        host=config['POSTGRESQL']['host'],
        port=config['POSTGRESQL']['port'],
        database=config['POSTGRESQL']['database'],
        user=config['POSTGRESQL']['user'],
        password=config['POSTGRESQL']['password']
    )
    
    schema = config['POSTGRESQL']['schema']
    
    # Test cases: (table, columns)
    test_cases = [
        ('cast_info', ['note']),
        ('cast_info', ['note', 'person_id']),
        ('movie_companies', ['note']),
        ('movie_companies', ['note', 'company_id']),
        ('movie_info', ['info']),
        ('aka_name', ['name']),
        ('char_name', ['name']),
        ('person_info', ['note']),
    ]
    
    cursor = conn.cursor()
    
    print("Testing index creation with size limits...")
    print("=" * 70)
    
    for table, columns in test_cases:
        test_idx_name = f"test_idx_{table}_{'_'.join(columns)}"
        col_list = ', '.join(columns)
        
        # Check column types first
        cursor.execute(f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s AND column_name = ANY(%s)
        """, (schema, table, columns))
        
        col_info = cursor.fetchall()
        print(f"\n{table}({col_list}):")
        for col_name, dtype, max_len in col_info:
            print(f"  - {col_name}: {dtype} (max_len: {max_len})")
        
        # Try to create index
        try:
            cursor.execute(f'DROP INDEX IF EXISTS {schema}.{test_idx_name}')
            cursor.execute(f'CREATE INDEX {test_idx_name} ON {schema}.{table} ({col_list})')
            conn.commit()
            print(f"  ✓ Index created successfully")
            cursor.execute(f'DROP INDEX IF EXISTS {schema}.{test_idx_name}')
            conn.commit()
        except psycopg2.errors.ProgramLimitExceeded as e:
            conn.rollback()
            print(f"  ✗ FAILED: Index row size exceeds limit")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ FAILED: {str(e)[:100]}")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    conn.close()

if __name__ == "__main__":
    test_index_creation()
