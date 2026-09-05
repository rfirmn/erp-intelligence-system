-- ==============================================================================
-- ISP MVP BI DATABASE SCHEMA (Mock ERP External Source)
-- Dialect: PostgreSQL 16
-- Domain: Data Engineering Mock ERP Database (Source System)
-- ==============================================================================

-- Clean state
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- ==============================================================================
-- 1. ORGANIZATION & USER ACCESS
-- ==============================================================================

CREATE TABLE department (
    id SERIAL PRIMARY KEY,
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee (
    id SERIAL PRIMARY KEY,
    department_id INTEGER REFERENCES department(id),
    employee_code VARCHAR(50) UNIQUE NOT NULL,
    employee_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(30),
    position VARCHAR(50),
    hire_date DATE,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_account (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER UNIQUE NOT NULL REFERENCES employee(id),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 2. ISP MASTER DATA
-- ==============================================================================

CREATE TABLE internet_package (
    id SERIAL PRIMARY KEY,
    package_code VARCHAR(50) UNIQUE NOT NULL,
    package_name VARCHAR(100) NOT NULL,
    speed_mbps INTEGER,
    monthly_price NUMERIC(15, 2) NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customer (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(30),
    address TEXT,
    city VARCHAR(50),
    installation_date DATE,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customer_subscription (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    package_id INTEGER NOT NULL REFERENCES internet_package(id),
    subscription_no VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    monthly_fee NUMERIC(15, 2) NOT NULL,
    billing_day INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 3. SUPPLIER & INVENTORY
-- ==============================================================================

CREATE TABLE supplier (
    id SERIAL PRIMARY KEY,
    supplier_code VARCHAR(50) UNIQUE NOT NULL,
    supplier_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(30),
    address TEXT,
    city VARCHAR(50),
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE item (
    id SERIAL PRIMARY KEY,
    item_code VARCHAR(50) UNIQUE NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit VARCHAR(20),
    description TEXT,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warehouse (
    id SERIAL PRIMARY KEY,
    warehouse_code VARCHAR(50) UNIQUE NOT NULL,
    warehouse_name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock (
    id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouse(id),
    item_id INTEGER NOT NULL REFERENCES item(id),
    quantity INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_warehouse_item UNIQUE (warehouse_id, item_id)
);

CREATE TABLE stock_ledger (
    id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouse(id),
    item_id INTEGER NOT NULL REFERENCES item(id),
    employee_id INTEGER REFERENCES employee(id),
    reference_type VARCHAR(50),
    reference_id INTEGER,
    qty_in INTEGER DEFAULT 0,
    qty_out INTEGER DEFAULT 0,
    balance_qty INTEGER NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 4. PROCUREMENT
-- ==============================================================================

CREATE TABLE purchase_order (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES supplier(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouse(id),
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_date DATE NOT NULL,
    tax_amount NUMERIC(15, 2) DEFAULT 0,
    discount NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'APPROVED',
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_order_item (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL REFERENCES purchase_order(id),
    item_id INTEGER NOT NULL REFERENCES item(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(15, 2) NOT NULL,
    line_total NUMERIC(15, 2) NOT NULL
);

CREATE TABLE purchase_invoice (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER UNIQUE NOT NULL REFERENCES purchase_order(id),
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    tax_amount NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'UNPAID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_payment (
    id SERIAL PRIMARY KEY,
    purchase_invoice_id INTEGER NOT NULL REFERENCES purchase_invoice(id),
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 5. ISP BILLING & SALES
-- ==============================================================================

CREATE TABLE sales_invoice (
    id SERIAL PRIMARY KEY,
    customer_subscription_id INTEGER NOT NULL REFERENCES customer_subscription(id),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_period DATE NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    subtotal NUMERIC(15, 2) NOT NULL,
    tax_amount NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'UNPAID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_payment (
    id SERIAL PRIMARY KEY,
    sales_invoice_id INTEGER NOT NULL REFERENCES sales_invoice(id),
    employee_id INTEGER REFERENCES employee(id),
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'SUCCESS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 6. ACCOUNTING (MINIMAL)
-- ==============================================================================

CREATE TABLE account (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL
);

CREATE TABLE journal_entry (
    id BIGSERIAL PRIMARY KEY,
    entry_no VARCHAR(50) UNIQUE NOT NULL,
    entry_date DATE NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES employee(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE journal_entry_line (
    id BIGSERIAL PRIMARY KEY,
    journal_entry_id BIGINT NOT NULL REFERENCES journal_entry(id),
    account_id INTEGER NOT NULL REFERENCES account(id),
    debit NUMERIC(15, 2) DEFAULT 0,
    credit NUMERIC(15, 2) DEFAULT 0
);

-- ==============================================================================
-- 7. ASSET & AUDIT
-- ==============================================================================

CREATE TABLE asset (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employee(id),
    department_id INTEGER REFERENCES department(id),
    asset_code VARCHAR(50) UNIQUE NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    purchase_date DATE,
    asset_value NUMERIC(15, 2),
    status VARCHAR(30) DEFAULT 'IN_USE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_account_id INTEGER REFERENCES user_account(id),
    action VARCHAR(50) NOT NULL,
    module VARCHAR(50),
    table_name VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
