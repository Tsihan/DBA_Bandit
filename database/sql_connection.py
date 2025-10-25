import configparser

try:
    import pyodbc  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for MSSQL
    pyodbc = None

try:
    import psycopg2  # type: ignore
except ImportError as exc:  # pragma: no cover - must be installed for PostgreSQL usage
    psycopg2 = None

import constants


def get_sql_connection():
    """
    This method simply returns the sql connection based on the DB type and the connection settings
    defined in the db.conf
    :return: connection
    """

    # Reading the Database configurations
    db_config = configparser.ConfigParser()
    db_config.read(constants.DB_CONFIG)
    db_type = db_config.get('SYSTEM', 'db_type')

    if db_type.strip().upper() in {'POSTGRES', 'POSTGRESQL'}:
        if psycopg2 is None:
            raise ImportError("psycopg2 is required to connect to PostgreSQL databases.")
        pg_config = db_config[db_type]
        connect_kwargs = {
            'host': pg_config.get('host', 'localhost'),
            'port': pg_config.getint('port', fallback=5432),
            'dbname': pg_config.get('database'),
            'user': pg_config.get('user'),
            'password': pg_config.get('password'),
        }
        options = pg_config.get('options', fallback=None)
        if options:
            connect_kwargs['options'] = options

        # Remove None values to avoid overriding lib defaults
        connect_kwargs = {k: v for k, v in connect_kwargs.items() if v is not None and v != ''}
        connection = psycopg2.connect(**connect_kwargs)
        connection.autocommit = True
        return connection

    server = db_config[db_type]['server']
    database = db_config[db_type]['database']
    driver = db_config[db_type]['driver']

    if pyodbc is None:
        raise ImportError("pyodbc is required to connect to MSSQL databases.")

    return pyodbc.connect(
        r'Driver=' + driver + ';Server=' + server + ';Database=' + database + ';Trusted_Connection=yes;')


def close_sql_connection(connection):
    """
    Take care of the closing process of the SQL connection
    :param connection: sql_connection
    :return: operation status
    """
    return connection.close()
