#!/usr/bin/env python3
"""
Script to clean up existing indexes in IMDB database before running experiments.
This will drop all non-primary/non-unique indexes to ensure a clean starting point.
"""

import configparser
import psycopg2
from psycopg2 import sql

def clean_indexes():
    """Remove all non-system indexes from IMDB tables."""
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
    
    cursor = conn.cursor()
    
    # Find all non-constraint indexes
    query = """
        SELECT 
            schemaname,
            tablename,
            indexname
        FROM pg_indexes
        WHERE schemaname = %s
          AND indexname NOT LIKE 'pg_%'
          AND indexname NOT IN (
              SELECT conname 
              FROM pg_constraint 
              WHERE contype IN ('p', 'u')  -- primary key or unique
          )
        ORDER BY tablename, indexname;
    """
    
    cursor.execute(query, (schema,))
    indexes = cursor.fetchall()
    
    if not indexes:
        print(f"✅ No user-created indexes found in schema '{schema}'")
        conn.close()
        return
    
    print(f"Found {len(indexes)} user-created indexes to remove:")
    print("-" * 60)
    
    for schema_name, table_name, index_name in indexes:
        print(f"  {table_name:30s} -> {index_name}")
    
    print("-" * 60)
    print(f"\n⚠️  This will drop {len(indexes)} indexes!")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        conn.close()
        return
    
    print("\nDropping indexes...")
    dropped = 0
    failed = 0
    
    for schema_name, table_name, index_name in indexes:
        try:
            drop_stmt = sql.SQL("DROP INDEX IF EXISTS {}.{} CASCADE").format(
                sql.Identifier(schema_name),
                sql.Identifier(index_name)
            )
            cursor.execute(drop_stmt)
            conn.commit()
            print(f"  ✓ Dropped: {index_name}")
            dropped += 1
        except Exception as e:
            print(f"  ✗ Failed to drop {index_name}: {e}")
            failed += 1
            conn.rollback()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully dropped {dropped} indexes")
    if failed > 0:
        print(f"❌ Failed to drop {failed} indexes")
    print("=" * 60)
    print("\nDatabase is now ready for DBABandits experiments!")

if __name__ == "__main__":
    print("=" * 60)
    print("  IMDB Database Index Cleanup Tool")
    print("=" * 60)
    print()
    clean_indexes()
