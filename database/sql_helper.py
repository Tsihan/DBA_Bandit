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
    # Always reload to get latest code
    if module_name in importlib.sys.modules:
        module = importlib.reload(importlib.sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)
    return module

def __getattr__(name):
    """Dynamically forward attribute access to the implementation module."""
    _impl = _load_helper()
    if hasattr(_impl, name):
        return getattr(_impl, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def get_helper_metadata() -> Dict[str, str]:
    """Utility for callers that need to know which helper is active."""
    return {
        'module': _load_helper().__name__,
        'db_type': _CONFIG.get('SYSTEM', 'db_type', fallback='MSSQL').strip().upper(),
    }
