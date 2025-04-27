# test_component_integration.py - UPDATED
import logging
from src.core.di.container import Container
from src.core.events.event_bus import EventBus
from src.core.events.event_manager import EventManager
from src.core.events.event_types import EventType, Event
from src.core.events.event_emitters import BarEmitter
from src.data.sources.csv_handler import CSVDataSource
from src.data.historical_data_handler import HistoricalDataHandler
from src.risk.portfolio.portfolio import PortfolioManager

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_di_system():
    # Create DI container
    container = Container()
    
    # Register components
    container.register('event_bus', EventBus)
    
    # Register factory function for CSV source to provide data_dir parameter
    def create_csv_source(container):
        return CSVDataSource(data_dir="test_data")
    
    container.register_factory('csv_source', create_csv_source)
    
    # Register factory for bar emitter (requires event_bus)
    def create_bar_emitter(container):
        event_bus = container.get('event_bus')
        return BarEmitter("test_emitter", event_bus)
    
    container.register_factory('bar_emitter', create_bar_emitter)
    
    # Register components with dependencies
    container.register('event_manager', EventManager, 
                      dependencies={'event_bus': 'event_bus'})
    
    # Now register data_handler with all required dependencies
    def create_data_handler(container):
        data_source = container.get('csv_source')
        bar_emitter = container.get('bar_emitter')
        return HistoricalDataHandler(data_source, bar_emitter)
    
    container.register_factory('data_handler', create_data_handler)
    
    container.register('portfolio', PortfolioManager, 
                      dependencies={'event_bus': 'event_bus'})
    
    # Get components
    event_bus = container.get('event_bus')
    data_handler = container.get('data_handler')
    portfolio = container.get('portfolio')
    
    # Verify components were created
    logger.info(f"Created components:")
    logger.info(f"- EventBus: {event_bus}")
    logger.info(f"- DataHandler: {data_handler}")
    logger.info(f"- Portfolio: {portfolio}")
    
    return all([event_bus, data_handler, portfolio])

if __name__ == "__main__":
    success = test_di_system()
    logger.info(f"Integration test {'passed' if success else 'failed'}")
