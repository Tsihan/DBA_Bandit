-- Script to drop all user-created indexes from IMDB database
-- This prepares the database for DBABandits experiments
-- Run with: psql -U qihan -d imdbload -f scripts/drop_old_indexes.sql

\echo '====================================================================='
\echo 'Dropping all user-created indexes from IMDB database...'
\echo '====================================================================='
\echo ''

-- Drop indexes that might exist from previous runs or manual creation
-- Common IMDB table indexes

\echo 'Dropping indexes on title table...'
DROP INDEX IF EXISTS movie_id_movie_companies CASCADE;
DROP INDEX IF EXISTS movie_id_cast_info CASCADE;
DROP INDEX IF EXISTS movie_id_movie_keyword CASCADE;
DROP INDEX IF EXISTS movie_id_movie_info CASCADE;
DROP INDEX IF EXISTS movie_id_movie_info_idx CASCADE;
DROP INDEX IF EXISTS title_production_year_idx CASCADE;
DROP INDEX IF EXISTS title_kind_id_idx CASCADE;

\echo 'Dropping indexes on cast_info table...'
DROP INDEX IF EXISTS person_id_cast_info CASCADE;
DROP INDEX IF EXISTS cast_info_movie_id_idx CASCADE;
DROP INDEX IF EXISTS cast_info_person_id_idx CASCADE;
DROP INDEX IF EXISTS cast_info_role_id_idx CASCADE;

\echo 'Dropping indexes on movie_companies table...'
DROP INDEX IF EXISTS company_id_movie_companies CASCADE;
DROP INDEX IF EXISTS movie_companies_movie_id_idx CASCADE;
DROP INDEX IF EXISTS movie_companies_company_id_idx CASCADE;

\echo 'Dropping indexes on movie_keyword table...'
DROP INDEX IF EXISTS keyword_id_movie_keyword CASCADE;
DROP INDEX IF EXISTS movie_keyword_movie_id_idx CASCADE;
DROP INDEX IF EXISTS movie_keyword_keyword_id_idx CASCADE;

\echo 'Dropping indexes on movie_info table...'
DROP INDEX IF EXISTS movie_info_movie_id_idx CASCADE;
DROP INDEX IF EXISTS movie_info_info_type_id_idx CASCADE;

\echo 'Dropping indexes on movie_info_idx table...'
DROP INDEX IF EXISTS movie_info_idx_movie_id_idx CASCADE;
DROP INDEX IF EXISTS movie_info_idx_info_type_id_idx CASCADE;

\echo 'Dropping indexes on name table...'
DROP INDEX IF EXISTS name_gender_idx CASCADE;
DROP INDEX IF EXISTS name_pcode_cf_idx CASCADE;

\echo 'Dropping indexes on company_name table...'
DROP INDEX IF EXISTS company_name_country_code_idx CASCADE;

\echo 'Dropping indexes on keyword table...'
DROP INDEX IF EXISTS keyword_keyword_idx CASCADE;

\echo 'Dropping indexes on aka_name table...'
DROP INDEX IF EXISTS aka_name_person_id_idx CASCADE;

\echo 'Dropping indexes on person_info table...'
DROP INDEX IF EXISTS person_info_person_id_idx CASCADE;

\echo 'Dropping indexes on movie_link table...'
DROP INDEX IF EXISTS movie_link_linked_movie_id_idx CASCADE;

\echo 'Dropping indexes on char_name table...'
DROP INDEX IF EXISTS char_name_name_idx CASCADE;

\echo 'Dropping indexes on complete_cast table...'
DROP INDEX IF EXISTS complete_cast_movie_id_idx CASCADE;

\echo ''
\echo '====================================================================='
\echo 'Checking remaining user-created indexes...'
\echo '====================================================================='

-- Show all remaining non-system indexes
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
      WHERE contype IN ('p', 'u')
  )
ORDER BY tablename, indexname;

\echo ''
\echo '✅ Index cleanup complete!'
\echo ''
\echo 'If any indexes still appear above, you may need to drop them manually with:'
\echo 'DROP INDEX IF EXISTS index_name CASCADE;'
\echo ''
