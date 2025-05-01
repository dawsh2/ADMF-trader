# MA Crossover Signal Grouping Fix

This package provides a fix for the MA Crossover Signal Grouping issue where the system generates 54 trades while validation expects 18 trades.

## Problem Summary

- System generates **54 trades** while validation expects **18 trades** (3:1 ratio)
- Root cause: Mismatch in `rule_id` format between implementation and validation
- Impact