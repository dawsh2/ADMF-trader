graph TD
    %% Core components
    subgraph CoreSystem["Core System"]
        EventBus["Event Bus"]
        ConfigManager["Configuration Manager"]
        DIContainer["Dependency Injection Container"]
        EventTypes["Event Types"]
        Bootstrap["Bootstrap Process"]
    end
    
    %% Data components
    subgraph DataModule["Data Module"]
        DataSources["Data Sources"]
        DataHandlers["Data Handlers"]
        Transformers["Data Transformers"]
        Features["Feature Engineering"]
    end
    
    %% Strategy components
    subgraph StrategyModule["Strategy Module"]
        StrategyBase["Strategy Base"]
        Indicators["Technical Indicators"]
        Rules["Trading Rules"]
        SignalGeneration["Signal Generation"]
        MultiStrategy["Multi-Strategy Framework"]
    end
    
    %% Risk components
    subgraph RiskModule["Risk Module"]
        PositionTracking["Position Tracking"]
        RiskManagers["Risk Managers"]
        PortfolioManagement["Portfolio Management"]
        RiskMetrics["Risk Metrics"]
    end
    
    %% Execution components
    subgraph ExecutionModule["Execution Module"]
        BrokerInterface["Broker Interface"]
        OrderManagement["Order Management"]
        ExecutionAlgorithms["Execution Algorithms"]
        FillProcessing["Fill Processing"]
    end
    
    %% Analytics components
    subgraph AnalyticsModule["Analytics Module"]
        PerformanceMetrics["Performance Metrics"]
        TradeAnalysis["Trade Analysis"]
        Visualization["Visualization"]
        Reporting["Reporting"]
    end
    
    %% Optimization components
    subgraph OptimizationModule["Optimization Module"]
        Optimizers["Optimizers"]
        WalkForward["Walk Forward Analysis"]
        ObjectiveFunctions["Objective Functions"]
        ModelEvaluation["Model Evaluation"]
    end
    
    %% Regime detection components
    subgraph RegimeModule["Regime Module"]
        RegimeDetectors["Regime Detectors"]
        RegimeAdaptation["Regime Adaptation"]
        RegimeAnalysis["Regime Analysis"]
    end
    
    %% Event flow
    DataSources --> EventBus
    EventBus --> DataHandlers
    DataHandlers --> Transformers
    Transformers --> Features
    
    Features --> StrategyBase
    EventBus --> StrategyBase
    Indicators --> Rules
    Features --> Rules
    Rules --> SignalGeneration
    SignalGeneration --> MultiStrategy
    MultiStrategy --> EventBus
    
    EventBus --> RiskManagers
    RiskManagers --> OrderManagement
    PositionTracking --> PortfolioManagement
    PortfolioManagement --> RiskMetrics
    
    EventBus --> OrderManagement
    OrderManagement --> BrokerInterface
    BrokerInterface --> ExecutionAlgorithms
    ExecutionAlgorithms --> FillProcessing
    FillProcessing --> EventBus
    
    EventBus --> PerformanceMetrics
    PerformanceMetrics --> TradeAnalysis
    TradeAnalysis --> Visualization
    Visualization --> Reporting
    
    StrategyBase --> Optimizers
    Optimizers --> WalkForward
    WalkForward --> ObjectiveFunctions
    ObjectiveFunctions --> ModelEvaluation
    
    EventBus --> RegimeDetectors
    RegimeDetectors --> RegimeAdaptation
    RegimeAdaptation --> StrategyBase
    RegimeDetectors --> RegimeAnalysis
    
    %% Core connections
    ConfigManager --> DIContainer
    DIContainer --> Bootstrap
    Bootstrap --> EventBus
    EventTypes --> EventBus
    DIContainer --> DataModule
    DIContainer --> StrategyModule
    DIContainer --> RiskModule
    DIContainer --> ExecutionModule
    DIContainer --> AnalyticsModule
    DIContainer --> OptimizationModule
    DIContainer --> RegimeModule
