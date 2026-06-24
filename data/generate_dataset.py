"""
generate_dataset.py
Generates simulated inventory dataset for analysis.
Mimics a mid-size distribution warehouse (FMCG / industrial supplies).
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

# --- Products ---
products = [
    ("PRD-001", "Aceite de motor 10W-40 1L",     "Lubricantes",    12.50,  "litro"),
    ("PRD-002", "Filtro de aire tipo A",          "Filtros",         8.30,  "unidad"),
    ("PRD-003", "Correa de distribución K-Series","Repuestos",      22.00,  "unidad"),
    ("PRD-004", "Grasa industrial multipropósito","Lubricantes",     5.80,  "kg"),
    ("PRD-005", "Filtro de aceite universal",     "Filtros",         6.50,  "unidad"),
    ("PRD-006", "Bujía NGK estándar",             "Eléctrico",       3.20,  "unidad"),
    ("PRD-007", "Batería 12V 60Ah",               "Eléctrico",      95.00,  "unidad"),
    ("PRD-008", "Líquido de frenos DOT4 500ml",   "Fluidos",         7.40,  "litro"),
    ("PRD-009", "Refrigerante anticongelante 4L", "Fluidos",        14.20,  "litro"),
    ("PRD-010", "Pastillas de freno delantera",   "Repuestos",      28.00,  "par"),
    ("PRD-011", "Amortiguador delantero",         "Repuestos",      65.00,  "unidad"),
    ("PRD-012", "Cable de bujía 4 piezas",        "Eléctrico",      18.50,  "set"),
    ("PRD-013", "Termostato de motor",            "Repuestos",      12.00,  "unidad"),
    ("PRD-014", "Bomba de agua completa",         "Repuestos",      45.00,  "unidad"),
    ("PRD-015", "Aceite de transmisión 75W-90",   "Lubricantes",    16.80,  "litro"),
    ("PRD-016", "Disco de freno ventilado",       "Repuestos",      55.00,  "unidad"),
    ("PRD-017", "Sensor de oxígeno lambda",       "Eléctrico",      38.00,  "unidad"),
    ("PRD-018", "Manguera de radiador superior",  "Repuestos",       9.50,  "unidad"),
    ("PRD-019", "Rodamiento de rueda delantera",  "Repuestos",      32.00,  "unidad"),
    ("PRD-020", "Limpia parabrisas 600mm",        "Accesorios",      6.00,  "unidad"),
]

categories = list(set(p[2] for p in products))
warehouses = ["ALM-NORTE", "ALM-SUR", "ALM-CENTRAL"]
suppliers  = ["ProveedorAlfa", "ProveedorBeta", "ProveedorGamma", "ProveedorDelta"]

# ---------- PRODUCTS TABLE ----------
df_products = pd.DataFrame(products, columns=["product_id","product_name","category","unit_cost","unit_measure"])
df_products["reorder_point"] = np.random.randint(10, 50, len(df_products))
df_products["max_stock"]     = df_products["reorder_point"] * np.random.randint(4, 8, len(df_products))
df_products.to_csv("/home/claude/inventory-analysis/data/products.csv", index=False)

# ---------- INVENTORY TABLE ----------
inv_rows = []
for _, prod in df_products.iterrows():
    for wh in warehouses:
        stock = np.random.randint(0, int(prod["max_stock"]) + 1)
        inv_rows.append({
            "product_id":       prod["product_id"],
            "warehouse":        wh,
            "stock_units":      stock,
            "last_restock_date": (datetime(2024,1,1) + timedelta(days=np.random.randint(0,180))).strftime("%Y-%m-%d"),
            "unit_cost":        prod["unit_cost"],
        })
df_inventory = pd.DataFrame(inv_rows)
df_inventory["stock_value"] = df_inventory["stock_units"] * df_inventory["unit_cost"]
df_inventory.to_csv("/home/claude/inventory-analysis/data/inventory.csv", index=False)

# ---------- MOVEMENTS TABLE (purchases + sales) ----------
start_date = datetime(2024, 1, 1)
movements  = []
for day_offset in range(180):
    current_date = start_date + timedelta(days=day_offset)
    # 3–8 movements per day
    for _ in range(np.random.randint(3, 9)):
        prod    = random.choice(products)
        mvt_type = random.choices(["SALE", "PURCHASE", "ADJUSTMENT"], weights=[0.65, 0.28, 0.07])[0]
        qty = np.random.randint(1, 20) if mvt_type == "PURCHASE" else np.random.randint(1, 8)
        movements.append({
            "movement_id":   f"MOV-{len(movements)+1:05d}",
            "movement_date": current_date.strftime("%Y-%m-%d"),
            "product_id":    prod[0],
            "warehouse":     random.choice(warehouses),
            "movement_type": mvt_type,
            "quantity":      qty,
            "unit_cost":     prod[3],
            "supplier":      random.choice(suppliers) if mvt_type == "PURCHASE" else None,
        })

df_movements = pd.DataFrame(movements)
df_movements.to_csv("/home/claude/inventory-analysis/data/movements.csv", index=False)

print(f"✅ Dataset generado:")
print(f"   products.csv   → {len(df_products)} filas")
print(f"   inventory.csv  → {len(df_inventory)} filas")
print(f"   movements.csv  → {len(df_movements)} filas")
