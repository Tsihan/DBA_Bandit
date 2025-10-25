"""Database helper facade that dispatches to the engine specific implementation."""
import configparser
import importlib
import os
from types import ModuleType
from typing import Dict

import constants

_CONFIG = configparser.ConfigParser()
if os.path.exists(constants.DB_CONFIG):
    _CONFIG.read(constants.DB_CONFIG)

def _load_helper() -> ModuleType:
    db_type = _CONFIG.get('SYSTEM', 'db_type', fallback='MSSQL').strip().upper()
    module_name = 'database.sql_helper_v2'
    if db_type in {'POSTGRES', 'POSTGRESQL'}:
        module_name = 'database.sql_helper_postgres'
    module = importlib.import_module(module_name)
    return module

_impl = _load_helper()

__all__ = [name for name in dir(_impl) if not name.startswith('_')]

globals().update({name: getattr(_impl, name) for name in __all__})


def get_helper_metadata() -> Dict[str, str]:
    """Utility for callers that need to know which helper is active."""
    return {
        'module': _impl.__name__,
        'db_type': _CONFIG.get('SYSTEM', 'db_type', fallback='MSSQL').strip().upper(),
    }
