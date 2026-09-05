flowchart TD

    %% =========================================================
    %% 1. ERP MODULES / DATA PROVISIONING
    %% =========================================================

    subgraph Zone1 ["1. ERP Module & Data Provisioning"]

        subgraph ERP_Commercial ["Commercial / CRM"]
            CRM[Customer]
            Contract[Contract]
            Subscription[Subscription / Service]
            Billing[Billing / Invoice]
        end

        subgraph ERP_Finance ["Finance"]
            AR[Account Receivable]
            AP[Account Payable]
            GL[General Ledger]
            Cash[Cash Flow / Payment]
        end

        subgraph ERP_Procurement ["Procurement"]
            PR[Purchase Request]
            PO[Purchase Order]
            Vendor[Vendor]
            Receipt[Goods Receipt]
        end

        subgraph ERP_Inventory ["Inventory / Warehouse"]
            Stock[Stock]
            Warehouse[Warehouse]
            Material[Material]
            Movement[Stock Movement]
        end

        subgraph ERP_Asset ["Asset Management"]
            Asset[Network / Office Asset]
            Maintenance[Maintenance]
            Depreciation[Depreciation]
        end

        subgraph ERP_Service ["Service / Operations"]
            SO[Service Order]
            WO[Work Order]
            SLA[SLA]
            Ticket[Service Ticket]
        end


        CRM --> FS_Commercial[Feature Store Commercial]
        Contract --> FS_Commercial
        Subscription --> FS_Commercial
        Billing --> FS_Commercial

        AR --> FS_Finance[Feature Store Finance]
        AP --> FS_Finance
        GL --> FS_Finance
        Cash --> FS_Finance

        PR --> FS_Procurement[Feature Store Procurement]
        PO --> FS_Procurement
        Vendor --> FS_Procurement
        Receipt --> FS_Procurement

        Stock --> FS_Inventory[Feature Store Inventory]
        Warehouse --> FS_Inventory
        Material --> FS_Inventory
        Movement --> FS_Inventory

        Asset --> FS_Asset[Feature Store Asset]
        Maintenance --> FS_Asset
        Depreciation --> FS_Asset

        SO --> FS_Service[Feature Store Service]
        WO --> FS_Service
        SLA --> FS_Service
        Ticket --> FS_Service

    end


    %% =========================================================
    %% 2. ML PER ERP MODULE
    %% =========================================================

    subgraph Zone2 ["2. Predictive ML Layer"]

        FS_Commercial --> ML_Churn[
            Churn Prediction
            XGBoost
        ]

        FS_Commercial --> ML_Revenue[
            Revenue Forecast
            Time Series
        ]

        FS_Finance --> ML_Collection[
            Collection Risk
            Classification
        ]

        FS_Finance --> ML_Cashflow[
            Cash Flow Forecast
            Time Series
        ]

        FS_Procurement --> ML_LeadTime[
            Vendor / PO Lead Time
            Forecasting
        ]

        FS_Procurement --> ML_Vendor[
            Vendor Risk Scoring
            Classification
        ]

        FS_Inventory --> ML_Stockout[
            Stockout Risk
            Forecasting
        ]

        FS_Inventory --> ML_Demand[
            Material Demand Forecast
            Time Series
        ]

        FS_Asset --> ML_Maintenance[
            Predictive Maintenance
            Classification / Regression
        ]

        FS_Service --> ML_SLA[
            SLA Breach Prediction
            Survival Analysis
        ]

        FS_Service --> ML_WorkOrder[
            Work Order Delay Prediction
            Classification
        ]


        ML_Churn --> O_Commercial[
            Commercial Predictions
        ]

        ML_Revenue --> O_Commercial

        ML_Collection --> O_Finance[
            Finance Predictions
        ]

        ML_Cashflow --> O_Finance

        ML_LeadTime --> O_Procurement[
            Procurement Predictions
        ]

        ML_Vendor --> O_Procurement

        ML_Stockout --> O_Inventory[
            Inventory Predictions
        ]

        ML_Demand --> O_Inventory

        ML_Maintenance --> O_Asset[
            Asset Predictions
        ]

        ML_SLA --> O_Service[
            Service Predictions
        ]

        ML_WorkOrder --> O_Service

    end


    %% =========================================================
    %% 3. AGENT PER MODULE
    %% =========================================================

    subgraph Zone3 ["3. LangGraph Agentic Layer"]

        O_Commercial --> Agent_Commercial[
            Commercial Agent
        ]

        O_Finance --> Agent_Finance[
            Finance Agent
        ]

        O_Procurement --> Agent_Procurement[
            Procurement Agent
        ]

        O_Inventory --> Agent_Inventory[
            Inventory Agent
        ]

        O_Asset --> Agent_Asset[
            Asset Agent
        ]

        O_Service --> Agent_Service[
            Service Operations Agent
        ]


        %% Shared ERP Query Layer
        ERP_SQL[
            ERP Query Tool
            Transaction / Aggregation
        ]

        Agent_Commercial -.-> ERP_SQL
        Agent_Finance -.-> ERP_SQL
        Agent_Procurement -.-> ERP_SQL
        Agent_Inventory -.-> ERP_SQL
        Agent_Asset -.-> ERP_SQL
        Agent_Service -.-> ERP_SQL


        %% External Context
        Network[
            Network Monitoring
        ]

        Topology[
            Network Topology
        ]

        NOC[
            Qdrant
            NOC Ticket History
        ]

        Agent_Service -.-> Network
        Agent_Service -.-> Topology
        Agent_Service -.-> NOC

    end


    %% =========================================================
    %% 4. INSIGHT GENERATION
    %% =========================================================

    subgraph Zone4 ["4. Insight Generation Engine"]

        Agent_Commercial --> Compiler[
            LangGraph State Compiler
        ]

        Agent_Finance --> Compiler
        Agent_Procurement --> Compiler
        Agent_Inventory --> Compiler
        Agent_Asset --> Compiler
        Agent_Service --> Compiler


        Compiler --> LLM[
            LLM API
            Narrative Synthesis
        ]

        Compiler --> ChartGen[
            Chart Spec Generator
            Vega-Lite / Plotly
        ]


        O_Commercial -.-> ChartGen
        O_Finance -.-> ChartGen
        O_Procurement -.-> ChartGen
        O_Inventory -.-> ChartGen
        O_Asset -.-> ChartGen
        O_Service -.-> ChartGen


        LLM --> Validator[
            Response Validator
        ]

        ChartGen --> Validator

        Validator --> Output[
            Validated Insight Package
        ]

    end


    %% =========================================================
    %% 5. PRESENTATION
    %% =========================================================

    subgraph Zone5 ["5. Presentation / ERP Intelligence Dashboard"]

        Output --> Dashboard[
            Unified ERP Intelligence Dashboard
        ]

        Dashboard --> CommercialView[
            Commercial
        ]

        Dashboard --> FinanceView[
            Finance
        ]

        Dashboard --> ProcurementView[
            Procurement
        ]

        Dashboard --> InventoryView[
            Inventory
        ]

        Dashboard --> AssetView[
            Asset
        ]

        Dashboard --> ServiceView[
            Service / Operations
        ]

    end


    style Zone1 fill:#f9f9f9,stroke:#333,stroke-width:2px
    style Zone2 fill:#e6e6fa,stroke:#663399,stroke-width:2px
    style Zone3 fill:#e6f3ff,stroke:#0066cc,stroke-width:2px
    style Zone4 fill:#fff2e6,stroke:#ff9900,stroke-width:2px
    style Zone5 fill:#e6ffe6,stroke:#009933,stroke-width:2px