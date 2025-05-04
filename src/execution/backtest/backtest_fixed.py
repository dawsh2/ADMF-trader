def _generate_debug_report(self):
    """Generate a detailed debug report to help diagnose issues."""
    logger.info("======= DETAILED DEBUG REPORT =======")
    
    # Strategy state
    if hasattr(self.strategy, 'get_debug_info'):
        strategy_info = self.strategy.get_debug_info()
        logger.info(f"Strategy debug info: {strategy_info}")
    
    # Signal count
    signal_count = len(getattr(self.strategy, 'signals_history', []))
    logger.info(f"Total signals generated: {signal_count}")
    
    # Orders info
    if self.order_registry:
        orders = []
        if hasattr(self.order_registry, 'get_all_orders'):
            orders = self.order_registry.get_all_orders()
        elif hasattr(self.order_registry, 'get_active_orders'):
            orders = self.order_registry.get_active_orders()
            logger.info("Using get_active_orders() as get_all_orders() is not available")
        else:
            logger.warning("Order registry has neither get_all_orders nor get_active_orders method")
            
        logger.info(f"Total orders created: {len(orders)}")
        for order in orders:
            logger.info(f"Order: {order}")
            
        # Check if any orders were created but not filled
        pending_orders = []
        try:
            pending_orders = [o for o in orders if hasattr(o, 'status') and 
                             (o.status.name in ['CREATED', 'PENDING'] if hasattr(o.status, 'name') else str(o.status) in ['CREATED', 'PENDING'])]
        except Exception as e:
            logger.warning(f"Error checking for pending orders: {e}")
            
        if pending_orders:
            logger.info(f"WARNING: {len(pending_orders)} orders were created but not filled!")
            for o in pending_orders:
                logger.info(f"Pending order: {o}")
    else:
        logger.info("Order registry not available")
    
    # Risk manager state
    if self.risk_manager:
        risk_stats = self.risk_manager.get_stats() if hasattr(self.risk_manager, 'get_stats') else "Not available"
        logger.info(f"Risk manager stats: {risk_stats}")
        
        # Check signals processed vs. orders generated
        if hasattr(risk_stats, 'get') and 'signals_processed' in risk_stats and 'orders_generated' in risk_stats:
            signals = risk_stats['signals_processed']
            orders = risk_stats['orders_generated']
            if signals > 0 and orders == 0:
                logger.warning(f"Risk manager processed {signals} signals but generated 0 orders!")
                logger.warning("This suggests signals are being filtered or rejected by risk management rules")
    else:
        logger.info("Risk manager not available")
    
    # Portfolio state
    if self.portfolio:
        portfolio_state = self.portfolio.get_state() if hasattr(self.portfolio, 'get_state') else self.portfolio.__dict__
        logger.info(f"Final portfolio state: {portfolio_state}")
        
        # Check if trades were executed
        trades = self.portfolio.get_recent_trades() if hasattr(self.portfolio, 'get_recent_trades') else []
        logger.info(f"Total trades executed: {len(trades)}")
        if not trades:
            logger.warning("No trades were executed during the backtest!")
    else:
        logger.info("Portfolio not available")
    
    # Event system stats
    if hasattr(self, 'event_counts'):
        logger.info(f"Event counts: {self.event_counts}")
        
        # Check if events flow as expected
        if 'SIGNAL' in self.event_counts and 'ORDER' in self.event_counts:
            if self.event_counts['SIGNAL'] > 0 and self.event_counts['ORDER'] == 0:
                logger.warning("Signals were generated but no orders were created!")
                logger.warning("Check the risk manager or order event processing")
    
    # Data info
    if self.data_handler:
        data_info = {
            "total_bars": self.iterations,
            "symbols": self.data_handler.get_symbols(),
            "start_date": self.data_handler.get_start_date() if hasattr(self.data_handler, 'get_start_date') else None,
            "end_date": self.data_handler.get_end_date() if hasattr(self.data_handler, 'get_end_date') else None
        }
        logger.info(f"Data information: {data_info}")
        
        # Output first and last few data points
        for symbol in self.data_handler.get_symbols():
            if hasattr(self.data_handler, 'get_data_for_symbol'):
                data = self.data_handler.get_data_for_symbol(symbol)
                if hasattr(data, 'head') and hasattr(data, 'tail'):
                    logger.info(f"First 3 bars for {symbol}:")
                    logger.info(f"{data.head(3)}")
                    logger.info(f"Last 3 bars for {symbol}:")
                    logger.info(f"{data.tail(3)}")
    
    logger.info("======= END DEBUG REPORT =======")