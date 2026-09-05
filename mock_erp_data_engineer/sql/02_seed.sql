-- ==============================================================================
-- ISP MVP BI SEED DATA (Mock ERP External Source)
-- Dialect: PostgreSQL 16
-- Domain: Data Engineering Mock Dataset (Indonesian ISP Business & Retail)
-- ==============================================================================

-- 1. Departments
INSERT INTO department (id, department_code, department_name, description) VALUES
(1, 'DEP-NOC', 'Network Operations Center', 'Manajemen operasional jaringan fiber & routing'),
(2, 'DEP-CS', 'Customer Service & Billing', 'Layanan pelanggan, komplain, dan invoice'),
(3, 'DEP-FIN', 'Finance & Accounting', 'Pembukuan, arus kas, dan perpajakan'),
(4, 'DEP-LOG', 'Logistics & Warehouse', 'Pengelolaan gudang kabel, ONT, dan perlengkapan FO'),
(5, 'DEP-SALES', 'Sales & Marketing', 'Akuisisi pelanggan residential dan B2B');

-- 2. Employees
INSERT INTO employee (id, department_id, employee_code, employee_name, email, phone, position, hire_date, status) VALUES
(1, 1, 'EMP-001', 'Budi Santoso', 'budi.noc@isp.net.id', '081234567801', 'Network Engineer Lead', '2023-01-15', 'ACTIVE'),
(2, 2, 'EMP-002', 'Siti Rahmawati', 'siti.billing@isp.net.id', '081234567802', 'Billing Specialist', '2023-03-10', 'ACTIVE'),
(3, 3, 'EMP-003', 'Ahmad Fauzi', 'ahmad.finance@isp.net.id', '081234567803', 'Senior Accountant', '2022-11-01', 'ACTIVE'),
(4, 4, 'EMP-004', 'Dedi Kurniawan', 'dedi.warehouse@isp.net.id', '081234567804', 'Warehouse Coordinator', '2023-06-20', 'ACTIVE'),
(5, 5, 'EMP-005', 'Maya Indah', 'maya.sales@isp.net.id', '081234567805', 'Corporate Account Manager', '2023-08-01', 'ACTIVE');

-- 3. User Accounts (bcrypt hashes)
INSERT INTO user_account (id, employee_id, username, password_hash, role, is_active) VALUES
(1, 1, 'admin_noc', '$2b$12$e8Y4vLzP09H76t428qFse.KzZqYVf42W9Gg487t5.Vf49987t66t6', 'noc_admin', true),
(2, 2, 'billing_staff', '$2b$12$e8Y4vLzP09H76t428qFse.KzZqYVf42W9Gg487t5.Vf49987t66t6', 'billing_operator', true),
(3, 3, 'finance_lead', '$2b$12$e8Y4vLzP09H76t428qFse.KzZqYVf42W9Gg487t5.Vf49987t66t6', 'finance_manager', true);

-- 4. Internet Packages
INSERT INTO internet_package (id, package_code, package_name, speed_mbps, monthly_price, description, status) VALUES
(1, 'PKG-HOME-30', 'Home Starter 30 Mbps', 30, 275000.00, 'Paket internet fiber optik unlimited untuk rumah tangga kecil', 'ACTIVE'),
(2, 'PKG-HOME-50', 'Home Fast 50 Mbps', 50, 385000.00, 'Paket internet ideal streaming HD dan gaming keluarga', 'ACTIVE'),
(3, 'PKG-HOME-100', 'Home Ultra 100 Mbps', 100, 550000.00, 'Koneksi ultra cepat untuk smart home dan multi-user', 'ACTIVE'),
(4, 'PKG-BIZ-200', 'Business Pro 200 Mbps', 200, 1250000.00, 'Paket bisnis rasio 1:1 dengan static IP publik', 'ACTIVE'),
(5, 'PKG-ENT-500', 'Dedicated Enterprise 500 Mbps', 500, 4500000.00, 'Dedicated bandwidth SLA 99.8% dengan direct peering', 'ACTIVE');

-- 5. Customers
INSERT INTO customer (id, customer_code, customer_name, email, phone, address, city, installation_date, status) VALUES
(1001, 'CUST-001001', 'PT Sinergi Abadi Maju', 'it@sinergiabadi.co.id', '0215551001', 'Gedung Cyber 1 Lt. 3, Jl. Kuningan Barat', 'Jakarta Selatan', '2024-02-01', 'ACTIVE'),
(1002, 'CUST-001002', 'CV Bandung Kreatif Studio', 'halo@bandungkreatif.com', '0228881002', 'Jl. Dago Asri No. 45', 'Bandung', '2024-04-15', 'ACTIVE'),
(1003, 'CUST-001003', 'Hendra Wijaya (Rumah)', 'hendra.w@gmail.com', '081299881003', 'Cluster Anggrek Blok B2 No. 10', 'Tangerang', '2024-05-10', 'ACTIVE'),
(1004, 'CUST-001004', 'Klinik Medika Pratama', 'admin@medikapratama.id', '0317771004', 'Jl. Raya Darmo No. 88', 'Surabaya', '2024-06-01', 'SUSPENDED'),
(1005, 'CUST-001005', 'Kafe Ruang Seduh Bekasi', 'seduh@ruangseduh.co.id', '0218881005', 'Ruko Galaxy Blok A No. 12', 'Bekasi', '2024-03-20', 'TERMINATED'),
(1006, 'CUST-001006', 'Dina Kurnia Sari', 'dina.kurnia@yahoo.com', '081344551006', 'Perumahan Puri Indah Blok C3', 'Jakarta Barat', '2024-07-01', 'ACTIVE'),
(1007, 'CUST-001007', 'PT Citra Nusa Logistik', 'finance@citranusa.com', '0215551007', 'Kawasan Industri MM2100', 'Bekasi', '2024-01-10', 'ACTIVE'),
(1008, 'CUST-001008', 'Rizky Pratama', 'rizky.pratama@outlook.com', '081822331008', 'Apartemen Sudirman Park Unit 12B', 'Jakarta Pusat', '2024-08-15', 'ACTIVE');

-- 6. Customer Subscriptions
INSERT INTO customer_subscription (id, customer_id, package_id, subscription_no, start_date, end_date, monthly_fee, billing_day, status, updated_at) VALUES
(1, 1001, 4, 'SUB-ISP-20240001', '2024-02-01', NULL, 1250000.00, 1, 'ACTIVE', '2026-08-01 08:00:00'),
(2, 1002, 3, 'SUB-ISP-20240002', '2024-04-15', NULL, 550000.00, 15, 'ACTIVE', '2026-08-01 08:30:00'),
(3, 1003, 2, 'SUB-ISP-20240003', '2024-05-10', NULL, 385000.00, 10, 'ACTIVE', '2026-08-01 09:00:00'),
(4, 1004, 3, 'SUB-ISP-20240004', '2024-06-01', NULL, 550000.00, 1, 'SUSPENDED', '2026-08-10 14:00:00'),
(5, 1005, 1, 'SUB-ISP-20240005', '2024-03-20', '2026-07-31', 275000.00, 20, 'TERMINATED', '2026-07-31 18:00:00'),
(6, 1006, 2, 'SUB-ISP-20240006', '2024-07-01', NULL, 385000.00, 1, 'ACTIVE', '2026-08-01 09:15:00'),
(7, 1007, 5, 'SUB-ISP-20240007', '2024-01-10', NULL, 4500000.00, 10, 'ACTIVE', '2026-08-01 09:30:00'),
(8, 1008, 1, 'SUB-ISP-20240008', '2024-08-15', NULL, 275000.00, 15, 'ACTIVE', '2026-08-15 10:00:00');

-- 7. Suppliers
INSERT INTO supplier (id, supplier_code, supplier_name, email, phone, address, city, status) VALUES
(1, 'SUP-FIBER', 'PT Fiber Optik Perkasa', 'sales@fiberperkasa.co.id', '0218991001', 'Kawasan Industri Pulo Gadung', 'Jakarta Timur', 'ACTIVE'),
(2, 'SUP-ROUTER', 'PT Global Network Hardware', 'orders@globalnetwork.id', '0218991002', 'Harco Mangga Dua Lt. 2', 'Jakarta Pusat', 'ACTIVE');

-- 8. Items
INSERT INTO item (id, item_code, item_name, category, unit, description, status) VALUES
(1, 'ITM-ONT-01', 'Modem GPON ONT Dual-Band AC1200', 'CPE Hardware', 'PCS', 'Terminal pelanggan fiber optik dengan Wi-Fi dual band', 'ACTIVE'),
(2, 'ITM-RTR-02', 'Router Wi-Fi 6 AX3000 Gigabit', 'Networking', 'PCS', 'Router performa tinggi untuk pelanggan bisnis', 'ACTIVE'),
(3, 'ITM-DROP-1C', 'Kabel Dropcore FO 1 Core 1000M', 'Cabling', 'ROLL', 'Kabel fiber optik outdoor drop wire G657A', 'ACTIVE'),
(4, 'ITM-PATCH-SC', 'Patch Cord SC-UPC to SC-UPC 3M', 'Accessories', 'PCS', 'Kabel jumper fiber optik single-mode', 'ACTIVE');

-- 9. Warehouses
INSERT INTO warehouse (id, warehouse_code, warehouse_name, location, status) VALUES
(1, 'WH-JKT', 'Gudang Utama Jakarta', 'Jl. Daan Mogot KM 12, Cengkareng', 'ACTIVE'),
(2, 'WH-BDG', 'Gudang Regional Bandung', 'Jl. Soekarno Hatta No. 420, Batununggal', 'ACTIVE');

-- 10. Stocks
INSERT INTO stock (warehouse_id, item_id, quantity) VALUES
(1, 1, 450),
(1, 2, 120),
(1, 3, 35),
(1, 4, 800),
(2, 1, 150),
(2, 3, 12);

-- 11. Stock Ledgers
INSERT INTO stock_ledger (warehouse_id, item_id, employee_id, reference_type, reference_id, qty_in, qty_out, balance_qty, remarks) VALUES
(1, 1, 4, 'INITIAL_STOCK', 1, 500, 0, 500, 'Saldo awal pembukuan tahunan'),
(1, 1, 4, 'INSTALLATION', 1001, 0, 1, 499, 'Pemasangan ke pelanggan SUB-ISP-20240001'),
(1, 1, 4, 'INSTALLATION', 1002, 0, 1, 498, 'Pemasangan ke pelanggan SUB-ISP-20240002');

-- 12. Purchase Orders & Items
INSERT INTO purchase_order (id, supplier_id, warehouse_id, employee_id, order_number, order_date, total_amount, status) VALUES
(1, 1, 1, 4, 'PO-2026-001', '2026-06-01', 25000000.00, 'RECEIVED'),
(2, 2, 1, 4, 'PO-2026-002', '2026-07-05', 48000000.00, 'RECEIVED');

INSERT INTO purchase_order_item (purchase_order_id, item_id, quantity, unit_price, line_total) VALUES
(1, 3, 20, 1250000.00, 25000000.00),
(2, 1, 100, 480000.00, 48000000.00);

-- 13. Purchase Invoices & Payments
INSERT INTO purchase_invoice (id, purchase_order_id, employee_id, invoice_number, invoice_date, due_date, total_amount, payment_status) VALUES
(1, 1, 3, 'PINV-2026-001', '2026-06-10', '2026-07-10', 25000000.00, 'PAID'),
(2, 2, 3, 'PINV-2026-002', '2026-07-12', '2026-08-12', 48000000.00, 'PAID');

INSERT INTO purchase_payment (id, purchase_invoice_id, employee_id, payment_number, payment_method, payment_date, amount, payment_status) VALUES
(1, 1, 3, 'PPAY-2026-001', 'BANK_TRANSFER_BCA', '2026-06-25', 25000000.00, 'COMPLETED'),
(2, 2, 3, 'PPAY-2026-002', 'BANK_TRANSFER_MANDIRI', '2026-07-28', 48000000.00, 'COMPLETED');

-- 14. Sales Invoices (Billing Cycles)
INSERT INTO sales_invoice (id, customer_subscription_id, invoice_number, invoice_period, invoice_date, due_date, subtotal, tax_amount, total_amount, payment_status, updated_at) VALUES
-- Subscription 1 (1.25M)
(1, 1, 'INV/202606/000001', '2026-06-01', '2026-06-01', '2026-06-15', 1250000.00, 0.00, 1250000.00, 'PAID', '2026-06-10 10:00:00'),
(2, 1, 'INV/202607/000002', '2026-07-01', '2026-07-01', '2026-07-15', 1250000.00, 0.00, 1250000.00, 'PAID', '2026-07-12 11:00:00'),
(3, 1, 'INV/202608/000003', '2026-08-01', '2026-08-01', '2026-08-15', 1250000.00, 0.00, 1250000.00, 'PAID', '2026-08-14 14:00:00'),
-- Subscription 2 (550K)
(4, 2, 'INV/202606/000004', '2026-06-01', '2026-06-15', '2026-06-29', 550000.00, 0.00, 550000.00, 'PAID', '2026-06-28 09:00:00'),
(5, 2, 'INV/202607/000005', '2026-07-01', '2026-07-15', '2026-07-29', 550000.00, 0.00, 550000.00, 'PAID', '2026-07-29 15:00:00'),
(6, 2, 'INV/202608/000006', '2026-08-01', '2026-08-15', '2026-08-29', 550000.00, 0.00, 550000.00, 'PAID', '2026-08-20 16:00:00'),
-- Subscription 3 (385K)
(7, 3, 'INV/202606/000007', '2026-06-01', '2026-06-10', '2026-06-24', 385000.00, 0.00, 385000.00, 'PAID', '2026-06-20 10:00:00'),
(8, 3, 'INV/202607/000008', '2026-07-01', '2026-07-10', '2026-07-24', 385000.00, 0.00, 385000.00, 'PAID', '2026-07-22 13:00:00'),
(9, 3, 'INV/202608/000009', '2026-08-01', '2026-08-10', '2026-08-24', 385000.00, 0.00, 385000.00, 'PAID', '2026-08-24 09:00:00'),
-- Subscription 4 (Late / Suspended)
(10, 4, 'INV/202606/000010', '2026-06-01', '2026-06-01', '2026-06-15', 550000.00, 0.00, 550000.00, 'PAID', '2026-06-20 10:00:00'),
(11, 4, 'INV/202607/000011', '2026-07-01', '2026-07-01', '2026-07-15', 550000.00, 0.00, 550000.00, 'OVERDUE', '2026-08-01 08:00:00'),
(12, 4, 'INV/202608/000012', '2026-08-01', '2026-08-01', '2026-08-15', 550000.00, 0.00, 550000.00, 'UNPAID', '2026-08-15 08:00:00'),
-- Subscription 5 (Terminated)
(13, 5, 'INV/202606/000013', '2026-06-01', '2026-06-20', '2026-07-04', 275000.00, 0.00, 275000.00, 'PAID', '2026-07-02 12:00:00'),
(14, 5, 'INV/202607/000014', '2026-07-01', '2026-07-20', '2026-08-03', 275000.00, 0.00, 275000.00, 'UNPAID', '2026-08-03 10:00:00');

-- 15. Sales Payments
INSERT INTO sales_payment (id, sales_invoice_id, employee_id, payment_number, payment_method, payment_date, amount, payment_status, created_at) VALUES
(1, 1, 2, 'SPAY-202606-001', 'VIRTUAL_ACCOUNT_BCA', '2026-06-10', 1250000.00, 'SUCCESS', '2026-06-10 10:05:00'),
(2, 2, 2, 'SPAY-202607-002', 'VIRTUAL_ACCOUNT_BCA', '2026-07-12', 1250000.00, 'SUCCESS', '2026-07-12 11:05:00'),
(3, 3, 2, 'SPAY-202608-003', 'VIRTUAL_ACCOUNT_BCA', '2026-08-14', 1250000.00, 'SUCCESS', '2026-08-14 14:05:00'),
(4, 4, 2, 'SPAY-202606-004', 'QRIS', '2026-06-28', 550000.00, 'SUCCESS', '2026-06-28 09:10:00'),
(5, 5, 2, 'SPAY-202607-005', 'QRIS', '2026-07-29', 550000.00, 'SUCCESS', '2026-07-29 15:10:00'),
(6, 6, 2, 'SPAY-202608-006', 'QRIS', '2026-08-20', 550000.00, 'SUCCESS', '2026-08-20 16:10:00'),
(7, 7, 2, 'SPAY-202606-007', 'CREDIT_CARD', '2026-06-20', 385000.00, 'SUCCESS', '2026-06-20 10:15:00'),
(8, 8, 2, 'SPAY-202607-008', 'CREDIT_CARD', '2026-07-22', 385000.00, 'SUCCESS', '2026-07-22 13:15:00'),
(9, 9, 2, 'SPAY-202608-009', 'CREDIT_CARD', '2026-08-24', 385000.00, 'SUCCESS', '2026-08-24 09:15:00'),
(10, 10, 2, 'SPAY-202606-010', 'VIRTUAL_ACCOUNT_MANDIRI', '2026-06-20', 550000.00, 'SUCCESS', '2026-06-20 10:20:00'),
(11, 13, 2, 'SPAY-202607-011', 'INDOMARET_RETAIL', '2026-07-02', 275000.00, 'SUCCESS', '2026-07-02 12:10:00');

-- 16. Chart of Accounts
INSERT INTO account (id, account_code, account_name, account_type) VALUES
(1, '1001', 'Kas Operasional Bank BCA', 'ASSET'),
(2, '1002', 'Kas Operasional Bank Mandiri', 'ASSET'),
(3, '1101', 'Piutang Pelanggan Internet', 'ASSET'),
(4, '1301', 'Persediaan Perangkat Jaringan', 'ASSET'),
(5, '2001', 'Utang Usaha Supplier', 'LIABILITY'),
(6, '4001', 'Pendapatan Langganan Internet', 'REVENUE'),
(7, '5001', 'Beban Bandwidth Transit / NAP', 'EXPENSE'),
(8, '5002', 'Beban Gaji & Operasional', 'EXPENSE');

-- 17. Journal Entries
INSERT INTO journal_entry (id, entry_no, entry_date, description, created_by) VALUES
(1, 'JRN-202606-001', '2026-06-01', 'Pengakuan Pendapatan & Piutang Billing Juni 2026', 3),
(2, 'JRN-202606-002', '2026-06-10', 'Penerimaan Kas Pembayaran Invoice PT Sinergi Abadi', 3);

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit, credit) VALUES
(1, 3, 2960000.00, 0.00),
(1, 6, 0.00, 2960000.00),
(2, 1, 1250000.00, 0.00),
(2, 3, 0.00, 1250000.00);

-- 18. Assets
INSERT INTO asset (id, employee_id, department_id, asset_code, asset_name, category, purchase_date, asset_value, status) VALUES
(1, 1, 1, 'AST-OLT-01', 'Huawei SmartAX MA5800 OLT 16-Port', 'Core Network', '2023-01-10', 145000000.00, 'IN_USE'),
(2, 1, 1, 'AST-RTR-01', 'MikroTik CCR2216-1G-12XS-2XQ Cloud Router', 'Routing Core', '2023-05-15', 42000000.00, 'IN_USE'),
(3, 4, 4, 'AST-SPL-01', 'Fujikura 90S+ Core Alignment Fusion Splicer', 'Field Equipment', '2023-02-20', 65000000.00, 'IN_USE');

-- 19. Audit Logs
INSERT INTO audit_log (id, user_account_id, action, module, table_name, description) VALUES
(1, 1, 'UPDATE_STATUS', 'SUBSCRIPTION', 'customer_subscription', 'Update status pelanggan SUB-ISP-20240004 menjadi SUSPENDED'),
(2, 2, 'GENERATE_BILLING', 'BILLING', 'sales_invoice', 'Generate tagihan otomatis periode Agustus 2026');

-- Update sequences to avoid duplicate key violations when adding new records
SELECT setval('department_id_seq', (SELECT MAX(id) FROM department));
SELECT setval('employee_id_seq', (SELECT MAX(id) FROM employee));
SELECT setval('user_account_id_seq', (SELECT MAX(id) FROM user_account));
SELECT setval('internet_package_id_seq', (SELECT MAX(id) FROM internet_package));
SELECT setval('customer_id_seq', (SELECT MAX(id) FROM customer));
SELECT setval('customer_subscription_id_seq', (SELECT MAX(id) FROM customer_subscription));
SELECT setval('supplier_id_seq', (SELECT MAX(id) FROM supplier));
SELECT setval('item_id_seq', (SELECT MAX(id) FROM item));
SELECT setval('warehouse_id_seq', (SELECT MAX(id) FROM warehouse));
SELECT setval('stock_id_seq', (SELECT MAX(id) FROM stock));
SELECT setval('stock_ledger_id_seq', (SELECT MAX(id) FROM stock_ledger));
SELECT setval('purchase_order_id_seq', (SELECT MAX(id) FROM purchase_order));
SELECT setval('purchase_order_item_id_seq', (SELECT MAX(id) FROM purchase_order_item));
SELECT setval('purchase_invoice_id_seq', (SELECT MAX(id) FROM purchase_invoice));
SELECT setval('purchase_payment_id_seq', (SELECT MAX(id) FROM purchase_payment));
SELECT setval('sales_invoice_id_seq', (SELECT MAX(id) FROM sales_invoice));
SELECT setval('sales_payment_id_seq', (SELECT MAX(id) FROM sales_payment));
SELECT setval('account_id_seq', (SELECT MAX(id) FROM account));
SELECT setval('journal_entry_id_seq', (SELECT MAX(id) FROM journal_entry));
SELECT setval('journal_entry_line_id_seq', (SELECT MAX(id) FROM journal_entry_line));
SELECT setval('asset_id_seq', (SELECT MAX(id) FROM asset));
SELECT setval('audit_log_id_seq', (SELECT MAX(id) FROM audit_log));
