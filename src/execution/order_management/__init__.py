"""
Order management module for handling order lifecycle.

This module focuses solely on order creation, routing, and tracking,
while leaving position and trade tracking to the Portfolio module.
"""
from .order_manager import OrderManager

__all__ = [
    'OrderManager'
]