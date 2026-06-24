#!/usr/bin/env python
# coding: utf-8

# # Inventory & Stock Rotation Analysis
# **Author:** Javier [Apellido]
# **Tools:** Python · Pandas · Matplotlib · Seaborn
# **Dataset:** Simulated warehouse data — 20 SKUs, 3 warehouses, 180 days

# ## 0. Setup

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
import os

warnings.filterwarnings("ignore")

# ── Style ─────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "#f8f8f8",
    "axes.grid":         True,
    "grid.color":        "white",
    "grid.linewidth":    1.0,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "font.family":       "DejaVu Sans",
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
})

PALETTE = ["#2563EB","#10B981","#F59E0B","#EF4444","#8B5CF6","#06B6D4"]
OUTPUT  = "reports/images"
os.makedirs(OUTPUT, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# ## 1. Load data
# ─────────────────────────────────────────────────────────────
products  = pd.read_csv("data/products.csv")
inventory = pd.read_csv("data/inventory.csv")
movements = pd.read_csv("data/movements.csv", parse_dates=["movement_date"])

print("── Dataset overview ───────────────────────────────────")
print(f"Products   : {len(products):>4} rows × {products.shape[1]} cols")
print(f"Inventory  : {len(inventory):>4} rows × {inventory.shape[1]} cols")
print(f"Movements  : {len(movements):>4} rows × {movements.shape[1]} cols")
print(f"Date range : {movements.movement_date.min().date()} → {movements.movement_date.max().date()}")
print()

# ─────────────────────────────────────────────────────────────
# ## 2. KPI calculation
# ─────────────────────────────────────────────────────────────

# 2.1 — Stock value by category
inv_merged = inventory.merge(products[["product_id","category","reorder_point","max_stock"]], on="product_id")
stock_by_cat = (
    inv_merged.groupby("category")
    .agg(
        total_units  = ("stock_units",  "sum"),
        total_value  = ("stock_value",  "sum"),
        sku_count    = ("product_id",   "nunique"),
    )
    .sort_values("total_value", ascending=False)
    .reset_index()
)

# 2.2 — Avg daily sales per product
sales = movements[movements["movement_type"] == "SALE"].copy()
days  = (movements.movement_date.max() - movements.movement_date.min()).days or 1

daily_sales = (
    sales.groupby("product_id")["quantity"]
    .sum()
    .div(days)
    .rename("avg_daily_sales")
    .reset_index()
)

# 2.3 — Current stock consolidated
current_stock = (
    inventory.groupby("product_id")
    .agg(total_stock=("stock_units","sum"), total_value=("stock_value","sum"))
    .reset_index()
)

# 2.4 — Days on hand + turnover
kpi = (
    products[["product_id","product_name","category","unit_cost","reorder_point","max_stock"]]
    .merge(current_stock, on="product_id", how="left")
    .merge(daily_sales,   on="product_id", how="left")
)
kpi["avg_daily_sales"]  = kpi["avg_daily_sales"].fillna(0)
kpi["days_on_hand"]     = kpi.apply(
    lambda r: round(r.total_stock / r.avg_daily_sales, 1) if r.avg_daily_sales > 0 else np.nan, axis=1
)
kpi["turnover_ratio"]   = kpi.apply(
    lambda r: round((r.avg_daily_sales * days) / max(r.total_stock, 0.001), 2), axis=1
)
kpi["stock_status"] = kpi["days_on_hand"].apply(
    lambda d: "CRÍTICO" if d < 15
         else "BAJO"    if d < 30
         else "NORMAL"  if d < 90
         else "EXCESO"  if pd.notna(d)
         else "SIN MOV."
)

# 2.5 — ABC classification
sales_rev = (
    sales.assign(revenue=lambda df: df["quantity"] * df["unit_cost"])
    .groupby("product_id")["revenue"].sum()
    .sort_values(ascending=False)
    .reset_index()
)
sales_rev["cum_pct"] = sales_rev["revenue"].cumsum() / sales_rev["revenue"].sum()
sales_rev["abc"] = sales_rev["cum_pct"].apply(
    lambda c: "A" if c <= 0.80 else ("B" if c <= 0.95 else "C")
)

print("── Key KPIs ───────────────────────────────────────────")
print(f"Total inventory value : ${inv_merged['stock_value'].sum():>10,.2f}")
print(f"Products below reorder: {(kpi['total_stock'] <= kpi['reorder_point']).sum():>4}")
print(f"Dead stock SKUs        : {kpi['days_on_hand'].isna().sum():>4}")
print(f"Avg days on hand       : {kpi['days_on_hand'].mean():>8.1f} days")
print(f"Avg turnover ratio     : {kpi['turnover_ratio'].mean():>8.2f}x")
print()

# ─────────────────────────────────────────────────────────────
# ## 3. Visualizations
# ─────────────────────────────────────────────────────────────

# ── Fig 1: Stock value by category ───────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Inventory Overview", fontsize=15, fontweight="bold", y=1.01)

ax = axes[0]
bars = ax.barh(stock_by_cat["category"], stock_by_cat["total_value"],
               color=PALETTE[:len(stock_by_cat)], edgecolor="white", height=0.6)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in stock_by_cat["total_value"]],
             padding=4, fontsize=9)
ax.set_title("Stock Value by Category (USD)")
ax.set_xlabel("Total Value (USD)")
ax.invert_yaxis()

ax = axes[1]
wedges, texts, autotexts = ax.pie(
    stock_by_cat["total_value"],
    labels=stock_by_cat["category"],
    autopct="%1.1f%%",
    colors=PALETTE[:len(stock_by_cat)],
    startangle=140,
    pctdistance=0.82,
    wedgeprops={"edgecolor":"white","linewidth":1.5},
)
for t in autotexts: t.set_fontsize(8)
ax.set_title("Distribution by Category")

plt.tight_layout()
plt.savefig(f"{OUTPUT}/01_stock_by_category.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 1 saved: stock_by_category")

# ── Fig 2: Days on hand + status ─────────────────────────────
kpi_sorted = kpi.dropna(subset=["days_on_hand"]).sort_values("days_on_hand")
status_colors = {"CRÍTICO":"#EF4444","BAJO":"#F59E0B","NORMAL":"#10B981","EXCESO":"#8B5CF6"}

fig, ax = plt.subplots(figsize=(13, 7))
bar_colors = [status_colors.get(s, "#94A3B8") for s in kpi_sorted["stock_status"]]
bars = ax.barh(kpi_sorted["product_name"], kpi_sorted["days_on_hand"],
               color=bar_colors, edgecolor="white", height=0.65)
ax.bar_label(bars, labels=[f"{v:.0f}d" for v in kpi_sorted["days_on_hand"]],
             padding=4, fontsize=8.5)
ax.axvline(15, color="#EF4444", lw=1.4, ls="--", label="Critical (15d)")
ax.axvline(30, color="#F59E0B", lw=1.4, ls="--", label="Low (30d)")
ax.axvline(90, color="#8B5CF6", lw=1.4, ls="--", label="Excess (90d)")
ax.set_title("Days of Inventory On Hand by Product", pad=12)
ax.set_xlabel("Days on Hand")
ax.legend(fontsize=9)
ax.invert_yaxis()

# Legend for status
from matplotlib.patches import Patch
legend_patches = [Patch(color=v, label=k) for k,v in status_colors.items()]
ax.legend(handles=legend_patches, loc="lower right", fontsize=9, title="Status")

plt.tight_layout()
plt.savefig(f"{OUTPUT}/02_days_on_hand.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 2 saved: days_on_hand")

# ── Fig 3: Turnover ratio (rotation) ─────────────────────────
turnover_sorted = kpi.sort_values("turnover_ratio", ascending=False).head(15)

fig, ax = plt.subplots(figsize=(13, 6))
bar_colors_t = ["#2563EB" if t >= 2 else "#F59E0B" if t >= 1 else "#EF4444"
                for t in turnover_sorted["turnover_ratio"]]
bars = ax.bar(range(len(turnover_sorted)), turnover_sorted["turnover_ratio"],
              color=bar_colors_t, edgecolor="white")
ax.bar_label(bars, labels=[f"{v:.1f}x" for v in turnover_sorted["turnover_ratio"]],
             padding=3, fontsize=8.5)
ax.set_xticks(range(len(turnover_sorted)))
ax.set_xticklabels([n.split()[0] for n in turnover_sorted["product_name"]],
                   rotation=35, ha="right", fontsize=8)
ax.axhline(2, color="#2563EB", lw=1.2, ls="--", alpha=0.6, label="Target ≥ 2x")
ax.set_title("Inventory Turnover Ratio (Top 15 Products)")
ax.set_ylabel("Turnover Ratio (×)")
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(f"{OUTPUT}/03_turnover_ratio.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 3 saved: turnover_ratio")

# ── Fig 4: Monthly sales vs purchases ────────────────────────
monthly = (
    movements[movements["movement_type"].isin(["SALE","PURCHASE"])]
    .assign(month=lambda df: df["movement_date"].dt.to_period("M"))
    .groupby(["month","movement_type"])
    .apply(lambda g: (g["quantity"] * g["unit_cost"]).sum())
    .reset_index(name="value")
)
monthly["month_str"] = monthly["month"].astype(str)
pivot = monthly.pivot(index="month_str", columns="movement_type", values="value").fillna(0)

fig, ax = plt.subplots(figsize=(13, 5))
x = np.arange(len(pivot))
w = 0.38
ax.bar(x - w/2, pivot.get("PURCHASE", 0), w, label="Purchases",
       color=PALETTE[0], edgecolor="white")
ax.bar(x + w/2, pivot.get("SALE",     0), w, label="Sales",
       color=PALETTE[1], edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(pivot.index, rotation=30, ha="right")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
ax.set_title("Monthly Purchases vs Sales (USD)")
ax.set_ylabel("Value (USD)")
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig(f"{OUTPUT}/04_monthly_trend.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 4 saved: monthly_trend")

# ── Fig 5: ABC Pareto chart ───────────────────────────────────
abc_merged = sales_rev.merge(products[["product_id","product_name"]], on="product_id")
abc_colors = {"A":"#2563EB","B":"#10B981","C":"#94A3B8"}

fig, ax1 = plt.subplots(figsize=(13, 6))
ax2 = ax1.twinx()

bar_colors_abc = [abc_colors[c] for c in abc_merged["abc"]]
ax1.bar(range(len(abc_merged)), abc_merged["revenue"],
        color=bar_colors_abc, edgecolor="white", zorder=2)
ax2.plot(range(len(abc_merged)), abc_merged["cum_pct"] * 100,
         color="#F59E0B", lw=2.2, marker="o", ms=4, zorder=3, label="Cumulative %")
ax2.axhline(80, color="#EF4444", lw=1.2, ls="--", alpha=0.7, label="80% mark")
ax2.axhline(95, color="#8B5CF6", lw=1.2, ls="--", alpha=0.7, label="95% mark")

ax1.set_xticks(range(len(abc_merged)))
ax1.set_xticklabels([n.split()[0] for n in abc_merged["product_name"]],
                    rotation=40, ha="right", fontsize=8)
ax1.set_ylabel("Revenue (USD)")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
ax2.set_ylabel("Cumulative Revenue %")
ax2.set_ylim(0, 115)
ax2.legend(loc="center right", fontsize=9)
ax1.set_title("ABC Analysis — Pareto Chart (Sales Revenue)")

from matplotlib.patches import Patch
legend_abc = [Patch(color=v, label=f"Class {k}") for k,v in abc_colors.items()]
ax1.legend(handles=legend_abc, loc="upper left", fontsize=9)

plt.tight_layout()
plt.savefig(f"{OUTPUT}/05_abc_pareto.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 5 saved: abc_pareto")

# ── Fig 6: Stock status summary (KPI dashboard) ──────────────
status_counts = kpi["stock_status"].value_counts()
all_statuses  = ["CRÍTICO","BAJO","NORMAL","EXCESO","SIN MOV."]
status_counts = status_counts.reindex(all_statuses, fill_value=0)
status_c      = ["#EF4444","#F59E0B","#10B981","#8B5CF6","#94A3B8"]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Stock Status Summary", fontsize=14, fontweight="bold")

ax = axes[0]
bars = ax.bar(status_counts.index, status_counts.values,
              color=status_c, edgecolor="white")
ax.bar_label(bars, padding=3, fontsize=11, fontweight="bold")
ax.set_title("SKUs by Stock Status")
ax.set_ylabel("Number of Products")
ax.set_xticklabels(status_counts.index, fontsize=9)

ax = axes[1]
below = kpi[kpi["total_stock"] <= kpi["reorder_point"]].copy()
below = below.merge(products[["product_id","product_name"]], on="product_id", how="left",
                    suffixes=("_kpi",""))
below["gap"] = below["reorder_point"] - below["total_stock"]
below = below.sort_values("gap", ascending=False).head(10)
ax.barh(below["product_name_kpi"] if "product_name_kpi" in below.columns
        else below["product_name"],
        below["gap"], color="#EF4444", edgecolor="white")
ax.set_title("Products Below Reorder Point\n(units short)")
ax.set_xlabel("Units Below Reorder Point")
ax.invert_yaxis()

plt.tight_layout()
plt.savefig(f"{OUTPUT}/06_stock_status.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Fig 6 saved: stock_status")

# ─────────────────────────────────────────────────────────────
# ## 4. Export summary report
# ─────────────────────────────────────────────────────────────
summary = kpi[["product_id","product_name","category","total_stock",
               "total_value","avg_daily_sales","days_on_hand",
               "turnover_ratio","stock_status"]].copy()
summary = summary.merge(sales_rev[["product_id","abc"]], on="product_id", how="left")
summary["abc"] = summary["abc"].fillna("N/A")
summary.to_csv("reports/inventory_analysis_report.csv", index=False)

print()
print("── Final Summary ──────────────────────────────────────")
print(summary[["product_name","days_on_hand","turnover_ratio","stock_status","abc"]]
      .to_string(index=False))
print()
print("✅ Analysis complete. Reports saved to reports/")
