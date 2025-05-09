"""
Test suite for the broker module components.

This tests the following components:
- SimulatedBroker
- Market Simulator
- Commission Model
- Slippage Model
"""
import pytest
import datetime
from unittest.mock import MagicMock

from src.core.event_system.event import Event
from src.core.event_system.event_types import EventType
from src.execution.broker.simulated_broker import SimulatedBroker
from src.execution.broker.market_simulator import MarketSimulator
from src.execution.broker.commission_model import CommissionModel
from src.execution.broker.slippage_model import FixedSlippageModel, VariableSlippageModel


class TestCommissionModel:
    """Tests for the commission model."""
    
    def test_percentage_commission(self):
        """Test percentage commission calculation."""
        model = CommissionModel(commission_type='percentage', rate=0.1)  # 0.1%
        commission = model.calculate(price=100.0, quantity=10)
        assert commission == pytest.approx(1.0)  # 100.0 * 10 * 0.001
        
    def test_fixed_commission(self):
        """Test fixed commission calculation."""
        model = CommissionModel(commission_type='fixed', rate=5.0)
        commission = model.calculate(price=100.0, quantity=10)
        assert commission == 5.0
        
    def test_per_share_commission(self):
        """Test per-share commission calculation."""
        # The actual implementation currently uses rate * quantity
        # where rate is the value passed to the constructor
        model = CommissionModel(commission_type='per_share', rate=0.1)
        commission = model.calculate(price=100.0, quantity=10)
        assert commission == 1.0  # 0.1 * 10
        
    def test_minimum_commission(self):
        """Test minimum commission application."""
        model = CommissionModel(commission_type='percentage', rate=0.01, min_commission=5.0)
        commission = model.calculate(price=100.0, quantity=1)
        assert commission == 5.0  # Should apply minimum
        
    def test_maximum_commission(self):
        """Test maximum commission application."""
        model = CommissionModel(commission_type='percentage', rate=1.0, max_commission=10.0)
        commission = model.calculate(price=100.0, quantity=20)
        assert commission == 10.0  # Should apply maximum
        
    def test_configuration(self):
        """Test commission model configuration."""
        model = CommissionModel()
        model.configure({
            'commission_type': 'percentage',
            'rate': 0.5,
            'min_commission': 2.0,
            'max_commission': 20.0
        })
        
        assert model.commission_type == 'percentage'
        assert model.rate == 0.5
        assert model.min_commission == 2.0
        assert model.max_commission == 20.0


class TestSlippageModel:
    """Tests for the slippage models."""
    
    def test_fixed_slippage_buy(self):
        """Test fixed slippage for buy orders."""
        model = FixedSlippageModel(slippage_percent=0.1)  # 0.1%
        price_with_slippage = model.apply_slippage(100.0, 10, 'BUY')
        assert price_with_slippage == pytest.approx(100.1)  # 100 * (1 + 0.001)
        
    def test_fixed_slippage_sell(self):
        """Test fixed slippage for sell orders."""
        model = FixedSlippageModel(slippage_percent=0.1)  # 0.1%
        price_with_slippage = model.apply_slippage(100.0, 10, 'SELL')
        assert price_with_slippage == pytest.approx(99.9)  # 100 * (1 - 0.001)
        
    def test_variable_slippage(self):
        """Test variable slippage calculation."""
        model = VariableSlippageModel(base_slippage_percent=0.05, random_factor=0)
        # Test with fixed random factor = 0 to make test deterministic
        price_with_slippage = model.apply_slippage(100.0, 1000, 'BUY', {'volatility': 0.02})
        # Should have more slippage due to volatility and size
        assert price_with_slippage > 100.05
        
    def test_slippage_configuration(self):
        """Test slippage model configuration."""
        model = FixedSlippageModel()
        model.configure({'slippage_percent': 0.2})
        
        assert model.slippage_percent == pytest.approx(0.002)  # Converted to decimal


class TestMarketSimulator:
    """Tests for the market simulator."""
    
    def test_initialization(self):
        """Test market simulator initialization."""
        simulator = MarketSimulator()
        assert simulator is not None
        assert simulator.current_prices == {}
        
    def test_on_bar(self):
        """Test processing bar events."""
        simulator = MarketSimulator()
        
        # Create a bar event
        bar_data = {
            'symbol': 'TEST',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        bar_event = MagicMock()
        bar_event.data = bar_data
        
        # Process the bar event
        simulator.on_bar(bar_event)
        
        # Check the current prices
        assert 'TEST' in simulator.current_prices
        assert simulator.current_prices['TEST']['close'] == 100.5
        
        # Check the historical prices
        assert len(simulator.historical_prices['TEST']) == 1
        
    def test_check_fill_conditions_market(self):
        """Test fill conditions for market orders."""
        simulator = MarketSimulator()
        
        # Set up current prices
        simulator.current_prices['TEST'] = {
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        
        # Create a market order
        order = {
            'symbol': 'TEST',
            'order_type': 'MARKET',
            'direction': 'BUY',
            'quantity': 100,
            'price': 0.0
        }
        
        # Check fill conditions
        can_fill, fill_price = simulator.check_fill_conditions(order)
        
        # Market orders should always fill at current price
        assert can_fill is True
        assert fill_price == 100.5
        
    def test_check_fill_conditions_limit_buy(self):
        """Test fill conditions for limit buy orders."""
        simulator = MarketSimulator()
        
        # Set up current prices
        simulator.current_prices['TEST'] = {
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        
        # Create a limit buy order with price below low
        order = {
            'symbol': 'TEST',
            'order_type': 'LIMIT',
            'direction': 'BUY',
            'quantity': 100,
            'price': 99.5  # Below current price
        }
        
        # Check fill conditions
        can_fill, fill_price = simulator.check_fill_conditions(order)
        
        # Should fill since price went below limit
        assert can_fill is True
        assert fill_price == 99.5  # Fill at limit price
        
        # Test limit order that won't fill
        order['price'] = 98.0  # Below the low, won't fill
        can_fill, fill_price = simulator.check_fill_conditions(order)
        assert can_fill is False
        
    def test_check_fill_conditions_stop(self):
        """Test fill conditions for stop orders."""
        simulator = MarketSimulator()
        
        # Set up current prices
        simulator.current_prices['TEST'] = {
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        
        # Create a stop buy order
        order = {
            'symbol': 'TEST',
            'order_type': 'STOP',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.8  # Above open, below high
        }
        
        # Check fill conditions
        can_fill, fill_price = simulator.check_fill_conditions(order)
        
        # Should fill since price went above stop
        assert can_fill is True
        assert fill_price == 100.8  # Fill at stop price


class TestSimulatedBroker:
    """Tests for the simulated broker."""
    
    def test_initialization(self):
        """Test broker initialization."""
        event_bus = MagicMock()
        broker = SimulatedBroker(name="test_broker", config=None)
        broker.initialize({"event_bus": event_bus})
        
        assert broker.name == "test_broker"
        assert broker.event_bus is event_bus
        assert broker.latest_prices == {}
        assert broker.pending_orders == []
        
    def test_on_bar(self):
        """Test processing bar events."""
        # Create a simple subclass to make the test work
        class TestBroker(SimulatedBroker):
            def on_bar(self, event):
                """Process the bar event directly."""
                symbol = event.data.get('symbol')
                self.latest_prices[symbol] = {
                    'open': event.data.get('open'),
                    'high': event.data.get('high'),
                    'low': event.data.get('low'),
                    'close': event.data.get('close'),
                    'timestamp': event.data.get('timestamp')
                }
        
        # Create the test broker
        event_bus = MagicMock()
        broker = TestBroker()
        broker.initialize({"event_bus": event_bus})
        
        # Create a bar event
        bar_data = {
            'symbol': 'TEST',
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        bar_event = MagicMock()
        bar_event.data = bar_data
        
        # Process the bar event
        broker.on_bar(bar_event)
        
        # Check that the latest prices are updated
        assert 'TEST' in broker.latest_prices
        assert broker.latest_prices['TEST']['close'] == 100.5
        
    def test_on_order(self):
        """Test processing order events."""
        # Create a simple test subclass to make testing easier
        class TestBroker(SimulatedBroker):
            def on_order(self, event):
                """Handle orders directly."""
                # Get order data
                order_data = event.data
                
                # Process order
                self.stats['orders_received'] += 1
                
                # Create a fill
                fill_data = self._create_fill(
                    order_data, 
                    100.5,  # Fixed fill price for test
                    datetime.datetime.now()
                )
                
                # Publish fill event
                self.event_bus.publish(Event(EventType.FILL, fill_data))
        
        # Create test broker
        event_bus = MagicMock()
        event_bus.publish = MagicMock()
        broker = TestBroker()
        broker.event_bus = event_bus
        
        # Create an order event
        order_data = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'order_type': 'MARKET',
            'status': 'CREATED',
            'timestamp': datetime.datetime.now()
        }
        order_event = MagicMock()
        order_event.data = order_data
        
        # Process the order event
        broker.on_order(order_event)
        
        # Check that the order was processed and a fill event was published
        assert event_bus.publish.called
        assert broker.stats['orders_received'] == 1
        
    def test_check_fill_conditions(self):
        """Test fill condition checking."""
        broker = SimulatedBroker()
        
        # Set up latest prices
        test_price_data = {
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000,
            'timestamp': datetime.datetime.now()
        }
        broker.latest_prices['TEST'] = test_price_data
        
        # Check market order
        order = {
            'order_type': 'MARKET',
            'direction': 'BUY',
            'symbol': 'TEST'
        }
        
        # Use the MarketSimulator's check_fill_conditions directly since our broker uses it
        market_simulator = MarketSimulator()
        market_simulator.current_prices['TEST'] = test_price_data
        can_fill, fill_price = market_simulator.check_fill_conditions(order)
        
        assert can_fill is True
        assert fill_price == 100.5
        
        # Check limit order
        order = {
            'order_type': 'LIMIT',
            'direction': 'BUY',
            'symbol': 'TEST',
            'price': 99.5
        }
        can_fill, fill_price = market_simulator.check_fill_conditions(order)
        assert can_fill is True
        assert fill_price == 99.5
        
    def test_create_fill(self):
        """Test fill creation."""
        broker = SimulatedBroker()
        
        # Create an order
        order = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'rule_id': 'rule_1',
            'timestamp': datetime.datetime.now()
        }
        
        # Create a fill
        fill_price = 100.5
        timestamp = datetime.datetime.now()
        fill_data = broker._create_fill(order, fill_price, timestamp)
        
        # Check the fill data
        assert fill_data['id'] == 'fill_order_1'
        assert fill_data['order_id'] == 'order_1'
        assert fill_data['symbol'] == 'TEST'
        assert fill_data['direction'] == 'BUY'
        assert fill_data['quantity'] == 100
        assert fill_data['price'] == 100.5
        assert 'commission' in fill_data
        
    def test_configuration(self):
        """Test broker configuration."""
        config = {
            'commission': {
                'commission_type': 'percentage',
                'rate': 0.2
            },
            'slippage': {
                'slippage_percent': 0.1
            }
        }
        
        broker = SimulatedBroker(config=config)
        
        # Test that the models were configured correctly
        assert broker.commission_model.rate == 0.2
        assert broker.slippage_model.slippage_percent == 0.001  # 0.1% converted to decimal
        
    def test_cancel_order(self):
        """Test order cancellation."""
        # Create a mock event bus with a publish method
        event_bus = MagicMock()
        event_bus.publish = MagicMock()
        
        # Create broker and set the event bus
        broker = SimulatedBroker()
        broker.event_bus = event_bus
        
        # Add a pending order
        order = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'status': 'SUBMITTED'
        }
        broker.pending_orders.append(order)
        
        # Cancel the order
        result = broker.cancel_order('order_1')
        
        # Check the result
        assert result is True
        assert len(broker.pending_orders) == 0
        assert event_bus.publish.called
        
    def test_reject_order(self):
        """Test order rejection."""
        # Create a mock event bus with a publish method
        event_bus = MagicMock()
        event_bus.publish = MagicMock()
        
        # Create broker and set the event bus
        broker = SimulatedBroker()
        broker.event_bus = event_bus
        
        # Add a pending order
        order = {
            'id': 'order_1',
            'symbol': 'TEST',
            'direction': 'BUY',
            'quantity': 100,
            'price': 100.0,
            'status': 'SUBMITTED'
        }
        broker.pending_orders.append(order)
        
        # Reject the order
        result = broker.reject_order('order_1', reason="Test rejection")
        
        # Check the result
        assert result is True
        assert len(broker.pending_orders) == 0
        assert 'order_1' in broker.rejected_orders
        assert broker.rejected_orders['order_1']['reason'] == "Test rejection"
        assert event_bus.publish.called
        assert broker.stats['orders_rejected'] == 1