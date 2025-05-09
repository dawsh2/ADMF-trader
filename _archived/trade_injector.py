#!/usr/bin/env python
"""
Trade Injector for ADMF-trader.

This script injects trades directly into the trade repository or portfolio,
bypassing the normal event flow to ensure trades are recorded.
"""

import os
import sys
import logging
import importlib
import inspect
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_injector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trade_injector')

def get_module(module_name):
    """Get a module if it exists"""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def find_class_in_module(module, class_name_pattern):
    """Find a class in