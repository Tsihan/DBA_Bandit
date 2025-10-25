-- Generic script to drop ALL user-created indexes
-- This queries the database for all non-system indexes and drops them
-- Run with: psql -U qihan -d imdbload -f scripts/drop_all_user_indexes.sql

\echo '====================================================================='
\echo 'Finding and dropping all user-created indexes...'
\echo '====================================================================='
\echo ''

-- Generate DROP statements for all user-created indexes
DO $$
DECLARE
    r RECORD;
    dropped_count INTEGER := 0;
BEGIN
    FOR r IN 
        SELECT 
            schemaname,
            tablename,
            indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname NOT LIKE 'pg_%'
          AND indexname NOT IN (
              SELECT conname 
              FROM pg_constraint 
              WHERE contype IN ('p', 'u', 'f')  -- primary, unique, foreign key
          )
        ORDER BY tablename, indexname
    LOOP
        BEGIN
            EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.indexname) || ' CASCADE';
            RAISE NOTICE 'Dropped: % on table %', r.indexname, r.tablename;
            dropped_count := dropped_count + 1;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Failed to drop %: %', r.indexname, SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '===================================================================';
    RAISE NOTICE 'Dropped % indexes', dropped_count;
    RAISE NOTICE '===================================================================';
END $$;

\echo ''
\echo 'Verifying cleanup...'
\echo ''

-- Show any remaining user-created indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname NOT LIKE 'pg_%'
  AND indexname NOT IN (
      SELECT conname 
      FROM pg_constraint 
      WHERE contype IN ('p', 'u', 'f')
  )
ORDER BY tablename, indexname;

\echo ''
\echo '✅ Cleanup complete! Database is ready for DBABandits experiments.'
\echo ''
