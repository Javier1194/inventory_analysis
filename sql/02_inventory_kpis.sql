-- ============================================================
-- 02_inventory_kpis.sql
-- Inventory KPI Analysis
-- Author: Javier [Apellido] | github.com/[tu-usuario]
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- KPI 1: Stock value by category
-- Total inventory value grouped by product category
-- ─────────────────────────────────────────────────────────────
SELECT
    p.category,
    COUNT(DISTINCT i.product_id)          AS total_products,
    SUM(i.stock_units)                    AS total_units,
    ROUND(SUM(i.stock_value)::NUMERIC, 2) AS total_stock_value,
    ROUND(AVG(i.stock_units)::NUMERIC, 1) AS avg_units_per_sku
FROM inventory i
JOIN products p ON i.product_id = p.product_id
GROUP BY p.category
ORDER BY total_stock_value DESC;


-- ─────────────────────────────────────────────────────────────
-- KPI 2: Inventory turnover ratio (last 180 days)
-- Formula: Cost of Goods Sold / Average Inventory Value
-- Higher = faster rotation (better)
-- ─────────────────────────────────────────────────────────────
WITH sales_cost AS (
    SELECT
        product_id,
        SUM(quantity * unit_cost) AS cogs
    FROM movements
    WHERE movement_type = 'SALE'
    GROUP BY product_id
),
avg_inventory AS (
    SELECT
        product_id,
        AVG(stock_value) AS avg_inv_value
    FROM inventory
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    ROUND(sc.cogs::NUMERIC, 2)                                    AS cogs_180d,
    ROUND(ai.avg_inv_value::NUMERIC, 2)                           AS avg_inventory_value,
    ROUND((sc.cogs / NULLIF(ai.avg_inv_value, 0))::NUMERIC, 2)   AS turnover_ratio,
    ROUND((180.0 / NULLIF(sc.cogs / NULLIF(ai.avg_inv_value,0), 0))::NUMERIC, 1) AS days_to_sell
FROM products p
LEFT JOIN sales_cost sc   ON p.product_id = sc.product_id
LEFT JOIN avg_inventory ai ON p.product_id = ai.product_id
ORDER BY turnover_ratio DESC NULLS LAST;


-- ─────────────────────────────────────────────────────────────
-- KPI 3: Days of inventory on hand (DOH)
-- Formula: (Current Stock / Avg Daily Sales) 
-- How many days of stock remain at current sales pace
-- ─────────────────────────────────────────────────────────────
WITH daily_sales AS (
    SELECT
        product_id,
        SUM(quantity) / 180.0 AS avg_daily_units_sold
    FROM movements
    WHERE movement_type = 'SALE'
    GROUP BY product_id
),
current_stock AS (
    SELECT
        product_id,
        SUM(stock_units) AS total_stock
    FROM inventory
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    cs.total_stock,
    ROUND(ds.avg_daily_units_sold::NUMERIC, 2)                               AS avg_daily_sales,
    ROUND((cs.total_stock / NULLIF(ds.avg_daily_units_sold, 0))::NUMERIC, 0) AS days_on_hand,
    CASE
        WHEN cs.total_stock / NULLIF(ds.avg_daily_units_sold,0) < 15  THEN 'CRÍTICO'
        WHEN cs.total_stock / NULLIF(ds.avg_daily_units_sold,0) < 30  THEN 'BAJO'
        WHEN cs.total_stock / NULLIF(ds.avg_daily_units_sold,0) < 90  THEN 'NORMAL'
        WHEN cs.total_stock / NULLIF(ds.avg_daily_units_sold,0) >= 90 THEN 'EXCESO'
        ELSE 'SIN MOVIMIENTO'
    END AS stock_status
FROM products p
LEFT JOIN daily_sales ds   ON p.product_id = ds.product_id
LEFT JOIN current_stock cs ON p.product_id = cs.product_id
ORDER BY days_on_hand ASC NULLS LAST;


-- ─────────────────────────────────────────────────────────────
-- KPI 4: Dead stock detection
-- Products with zero sales in the last 90 days
-- but with stock > 0
-- ─────────────────────────────────────────────────────────────
WITH recent_sales AS (
    SELECT DISTINCT product_id
    FROM movements
    WHERE movement_type = 'SALE'
      AND movement_date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(i.stock_units)  AS total_units_stuck,
    ROUND(SUM(i.stock_value)::NUMERIC, 2) AS capital_frozen_usd,
    i.last_restock_date
FROM inventory i
JOIN products p ON i.product_id = p.product_id
WHERE i.stock_units > 0
  AND p.product_id NOT IN (SELECT product_id FROM recent_sales)
GROUP BY p.product_id, p.product_name, p.category, i.last_restock_date
ORDER BY capital_frozen_usd DESC;


-- ─────────────────────────────────────────────────────────────
-- KPI 5: Stock below reorder point (replenishment alerts)
-- Products that need to be ordered NOW
-- ─────────────────────────────────────────────────────────────
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.reorder_point,
    SUM(i.stock_units)               AS current_stock,
    SUM(i.stock_units) - p.reorder_point AS units_below_reorder,
    p.max_stock - SUM(i.stock_units) AS units_to_order
FROM inventory i
JOIN products p ON i.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.reorder_point, p.max_stock
HAVING SUM(i.stock_units) <= p.reorder_point
ORDER BY units_below_reorder ASC;


-- ─────────────────────────────────────────────────────────────
-- KPI 6: Monthly purchase vs sales trend
-- ─────────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('month', movement_date)       AS month,
    movement_type,
    COUNT(*)                                 AS total_transactions,
    SUM(quantity)                            AS total_units,
    ROUND(SUM(quantity * unit_cost)::NUMERIC, 2) AS total_value_usd
FROM movements
WHERE movement_type IN ('SALE', 'PURCHASE')
GROUP BY DATE_TRUNC('month', movement_date), movement_type
ORDER BY month, movement_type;


-- ─────────────────────────────────────────────────────────────
-- KPI 7: Top 10 products by sales volume (Pareto / ABC analysis)
-- ─────────────────────────────────────────────────────────────
WITH product_sales AS (
    SELECT
        product_id,
        SUM(quantity * unit_cost) AS revenue
    FROM movements
    WHERE movement_type = 'SALE'
    GROUP BY product_id
),
ranked AS (
    SELECT
        ps.product_id,
        p.product_name,
        p.category,
        ps.revenue,
        SUM(ps.revenue) OVER ()                             AS total_revenue,
        SUM(ps.revenue) OVER (ORDER BY ps.revenue DESC
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue
    FROM product_sales ps
    JOIN products p ON ps.product_id = p.product_id
)
SELECT
    product_id,
    product_name,
    category,
    ROUND(revenue::NUMERIC, 2)                                          AS revenue_usd,
    ROUND((revenue / total_revenue * 100)::NUMERIC, 1)                  AS revenue_pct,
    ROUND((cumulative_revenue / total_revenue * 100)::NUMERIC, 1)       AS cumulative_pct,
    CASE
        WHEN cumulative_revenue / total_revenue <= 0.80 THEN 'A — Alto valor'
        WHEN cumulative_revenue / total_revenue <= 0.95 THEN 'B — Valor medio'
        ELSE                                                 'C — Bajo valor'
    END AS abc_classification
FROM ranked
ORDER BY revenue DESC;
