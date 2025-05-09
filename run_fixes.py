#!/usr/bin/env python3
"""
Script to run the symbol fixes and then execute the optimization
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_fixes.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_fixes')

def main():
    """Run the fixes and optimization"""
    logger.info("Starting fix and optimization process")
    
    # Step 1: Run the symbol fix script
    logger.info("Step 1: Running symbol fix script")
    try:
        from src.fix_strategy_symbols import fix_ma_crossover_strategy, force_config_symbols
        fix_ma_crossover_strategy()
        force_config_symbols()
        logger.info("Successfully ran symbol fixes