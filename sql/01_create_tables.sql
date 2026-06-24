-- ============================================================
-- 01_create_tables.sql
-- Inventory Analysis — Schema Definition
-- Compatible: PostgreSQL 13+ / SQLite 3.35+
-- ============================================================

-- Products master table
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(10)    PRIMARY KEY,
    product_name    VARCHAR(100)   NOT NULL,
    category        VARCHAR(50)    NOT NULL,
    unit_cost       DECIMAL(10,2)  NOT NULL,
    unit_measure    VARCHAR(20)    NOT NULL,
    reorder_point   INT            NOT NULL,
    max_stock       INT            NOT NULL
);

-- Current inventory by product and warehouse
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id      SERIAL PRIMARY KEY,  -- use INTEGER for SQLite
    product_id        VARCHAR(10)   NOT NULL REFERENCES products(product_id),
    warehouse         VARCHAR(20)   NOT NULL,
    stock_units       INT           NOT NULL DEFAULT 0,
    last_restock_date DATE,
    unit_cost         DECIMAL(10,2) NOT NULL,
    stock_value       DECIMAL(12,2) GENERATED ALWAYS AS (stock_units * unit_cost) STORED,
    UNIQUE (product_id, warehouse)
);

-- Stock movements (sales, purchases, adjustments)
CREATE TABLE IF NOT EXISTS movements (
    movement_id    VARCHAR(15)   PRIMARY KEY,
    movement_date  DATE          NOT NULL,
    product_id     VARCHAR(10)   NOT NULL REFERENCES products(product_id),
    warehouse      VARCHAR(20)   NOT NULL,
    movement_type  VARCHAR(15)   NOT NULL CHECK (movement_type IN ('SALE','PURCHASE','ADJUSTMENT')),
    quantity       INT           NOT NULL,
    unit_cost      DECIMAL(10,2) NOT NULL,
    supplier       VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_mov_product  ON movements(product_id);
CREATE INDEX IF NOT EXISTS idx_mov_date     ON movements(movement_date);
CREATE INDEX IF NOT EXISTS idx_mov_type     ON movements(movement_type);
