import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy import stats
from sklearn.base import clone
from sklearn.model_selection import KFold

from src.config import DATA_PATH, RANDOM_STATE
from src.data import load_data
from src.evaluation import cv_evaluate
from src.models import build_models
from src.preprocessing import clean_data, derive_physical_parameters

OUT = ROOT / "report_assets" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.edgecolor": "#334155",
        "axes.linewidth": 0.9,
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    }
)

TEAL = "#0F766E"
ORANGE = "#F97316"
BLUE = "#2563EB"
RED = "#DC2626"
PURPLE = "#7C3AED"
GOLD = "#CA8A04"
SLATE = "#64748B"
GRID = dict(color="#E2E8F0", linewidth=0.7)


def save(fig, name):
    path = OUT / name
    fig.savefig(path)
    plt.close(fig)
    print("saved", path)


def block_diagram():
    fig, ax = plt.subplots(figsize=(12.8, 4.9))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 5.15)
    ax.axis("off")

    def box(x, y, w, h, title, subtitle="", color="#E8F1EF", edge=TEAL):
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.06,rounding_size=0.12",
            linewidth=1.4,
            edgecolor=edge,
            facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2,
            y + h / 2 + (0.13 if subtitle else 0),
            title,
            ha="center",
            va="center",
            fontsize=10.2,
            fontweight="bold",
            color="#0F172A",
        )
        if subtitle:
            ax.text(
                x + w / 2,
                y + h / 2 - 0.18,
                subtitle,
                ha="center",
                va="center",
                fontsize=8.4,
                color="#334155",
            )

    def arrow(x1, y1, x2, y2):
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.4,
                color="#334155",
            )
        )

    top_y = 3.5
    w, h = 1.85, 1.05
    xs = [0.15, 2.27, 4.39, 6.51, 8.63, 10.75]
    labels = [
        ("T1.csv", "10-min SCADA"),
        ("Validation", "parse + dedupe"),
        ("Knot Detection", "cut-in / rated"),
        ("Model Bank", "8 regressors"),
        ("5-Fold CV", "out-of-fold error"),
        ("Best Model", "diagnostics"),
    ]
    for x, (t, s) in zip(xs, labels):
        box(x, top_y, w, h, t, s)
    for i in range(len(xs) - 1):
        arrow(xs[i] + w + 0.03, top_y + h / 2, xs[i + 1] - 0.03, top_y + h / 2)

    mid_y = 1.75
    box(2.35, mid_y, 2.55, 1.05, "Outlier Cleaning", "5 physical + robust rules", "#FFF4E8", ORANGE)
    box(5.55, mid_y, 2.55, 1.05, "Spline Regression", "cubic basis at knots", "#EAF0FE", BLUE)
    box(8.75, mid_y, 2.55, 1.05, "Evaluation", "RMSE / MAE / R2", "#F3EBFD", PURPLE)
    arrow(xs[1] + w / 2, top_y - 0.04, 3.62, mid_y + h + 0.04)
    arrow(4.9 + 0.03, mid_y + h / 2, 5.52, mid_y + h / 2)
    arrow(8.1 + 0.03, mid_y + h / 2, 8.72, mid_y + h / 2)

    ax.text(
        6.5,
        0.75,
        "Wind Turbine Power Curve Modelling using Spline Regression",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#0F172A",
    )
    ax.text(
        6.5,
        0.38,
        "Streamlit frontend  |  interactive diagnostics  |  reproducible outputs",
        ha="center",
        va="center",
        fontsize=9.5,
        color=SLATE,
    )
    save(fig, "fig_block_diagram.png")


def power_curve(cleaned, best_model, params):
    grid = np.linspace(0.0, 26.0, 800).reshape(-1, 1)
    pred = best_model.predict(grid)
    sample = cleaned.sample(min(7000, len(cleaned)), random_state=42)

    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ax.scatter(
        sample["wind_speed"],
        sample["power"],
        s=6,
        color="#94A3B8",
        alpha=0.30,
        linewidths=0,
        label="Observed power",
    )
    ax.plot(grid.ravel(), pred, color=TEAL, linewidth=2.8, label="Hybrid physical spline")
    ax.axvline(params["cut_in"], color=ORANGE, linestyle="--", linewidth=1.5)
    ax.axvline(params["rated"], color=RED, linestyle="--", linewidth=1.5)
    ax.text(params["cut_in"] - 0.15, 3640, "Cut-in\n3.0 m/s", color=ORANGE, ha="right", va="top", fontsize=9.5)
    ax.text(params["rated"] + 0.25, 3640, "Rated\n13.0 m/s", color=RED, ha="left", va="top", fontsize=9.5)
    ax.axvspan(0, params["cut_in"], color=ORANGE, alpha=0.05)
    ax.axvspan(params["cut_in"], params["rated"], color=BLUE, alpha=0.04)
    ax.axvspan(params["rated"], 26, color=RED, alpha=0.05)
    ax.text(1.3, 700, "Below cut-in", fontsize=9, color=ORANGE, rotation=90, va="bottom")
    ax.text(7.8, 3300, "Ramp region", fontsize=9, color=BLUE)
    ax.text(19.2, 3300, "Rated region", fontsize=9, color=RED)
    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Active power (kW)")
    ax.set_title("Fitted Power Curve with Physical Knots")
    ax.set_xlim(0, 26)
    ax.set_ylim(-60, 3900)
    ax.grid(True, **GRID)
    ax.legend(loc="lower right", frameon=True, framealpha=0.95)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_power_curve.png")


def model_comparison(cleaned, params):
    models = build_models(params)
    names = [
        "Linear regression",
        "Polynomial (degree 3)",
        "Piecewise linear (knots at cut-in and rated)",
        "Cubic B-spline (knots at cut-in and rated)",
        "Natural cubic spline (knots at cut-in and rated)",
        "Hybrid physical spline",
    ]
    colors = [RED, GOLD, PURPLE, BLUE, SLATE, TEAL]
    widths = [1.6, 1.6, 1.6, 2.0, 1.8, 3.0]
    grid = np.linspace(0.0, 26.0, 800).reshape(-1, 1)
    sample = cleaned.sample(min(3500, len(cleaned)), random_state=42)

    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ax.scatter(
        sample["wind_speed"],
        sample["power"],
        s=5,
        color="#CBD5E1",
        alpha=0.45,
        linewidths=0,
        label="Observed",
    )
    X = cleaned[["wind_speed"]].to_numpy(dtype=float)
    y = cleaned["power"].to_numpy(dtype=float)
    for name, color, width in zip(names, colors, widths):
        model = clone(models[name])
        model.fit(X, y)
        ax.plot(grid.ravel(), model.predict(grid), color=color, linewidth=width, label=name)
    ax.axvline(params["cut_in"], color="#94A3B8", linestyle=":", linewidth=1.2)
    ax.axvline(params["rated"], color="#94A3B8", linestyle=":", linewidth=1.2)
    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Active power (kW)")
    ax.set_title("Comparison of Fitted Power-Curve Models")
    ax.set_xlim(0, 26)
    ax.set_ylim(-60, 3850)
    ax.grid(True, **GRID)
    ax.legend(loc="upper left", fontsize=8.2, frameon=True, framealpha=0.95)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_model_comparison.png")


def cv_boxplot():
    folds = pd.read_csv(ROOT / "outputs" / "metrics" / "fold_results.csv")
    order = (
        folds.groupby("model")["rmse"].mean().sort_values(ascending=False).index.tolist()
    )
    data = [folds.loc[folds["model"] == m, "rmse"].to_numpy() for m in order]
    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    bp = ax.boxplot(
        data,
        vert=False,
        patch_artist=True,
        widths=0.55,
        medianprops=dict(color="#0F172A", linewidth=1.6),
        whiskerprops=dict(color="#475569"),
        capprops=dict(color="#475569"),
        flierprops=dict(marker="o", markersize=4, markerfacecolor=RED, markeredgecolor=RED, alpha=0.7),
    )
    palette = ["#DC2626", "#EA580C", "#CA8A04", "#7C3AED", "#2563EB", "#0D9488", "#0891B2", "#475569"]
    for patch, color in zip(bp["boxes"], palette):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
        patch.set_edgecolor(color)
    ax.set_yticklabels([m.replace(" (knots at cut-in and rated)", "") for m in order], fontsize=9)
    ax.set_xlabel("Cross-validated RMSE (kW)")
    ax.set_title("Fold-Level RMSE Distribution Across Models (5-Fold CV)")
    ax.grid(True, axis="x", **GRID)
    ax.set_xscale("log")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_cv_boxplot.png")


def diagnostics(cleaned, params):
    models = build_models(params)
    best = models["Hybrid physical spline"]
    X = cleaned[["wind_speed"]].to_numpy(dtype=float)
    y = cleaned["power"].to_numpy(dtype=float)
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    fold_results, oof = cv_evaluate({"best": best}, X, y, cv=cv)
    pred = oof["best"].to_numpy(dtype=float)
    resid = y - pred

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.9))
    ax = axes[0]
    ax.scatter(pred, resid, s=6, color=TEAL, alpha=0.28, linewidths=0)
    ax.axhline(0, color=RED, linewidth=1.2, linestyle="--")
    ax.set_xlabel("Fitted power (kW)")
    ax.set_ylabel("Residual (kW)")
    ax.set_title("Residuals vs Fitted (Out-of-Fold)")
    ax.grid(True, **GRID)

    ax = axes[1]
    ax.hist(resid, bins=70, color=BLUE, alpha=0.75, edgecolor="white", linewidth=0.3)
    ax.axvline(0, color=RED, linewidth=1.2, linestyle="--")
    ax.set_xlabel("Residual (kW)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Residuals")
    ax.grid(True, axis="y", **GRID)
    for a in axes:
        for spine in ("top", "right"):
            a.spines[spine].set_visible(False)
    fig.tight_layout()
    save(fig, "fig_residuals.png")

    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    (osm, osr), (slope, intercept, r) = stats.probplot(resid, dist="norm")
    ax.scatter(osm, osr, s=7, color=PURPLE, alpha=0.45, linewidths=0)
    ax.plot(osm, slope * osm + intercept, color=RED, linewidth=1.6)
    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Ordered residuals (kW)")
    ax.set_title("Normal Q-Q Plot of Residuals")
    ax.grid(True, **GRID)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_qq.png")

    fig, ax = plt.subplots(figsize=(6.6, 5.6))
    ax.scatter(y, pred, s=7, color=TEAL, alpha=0.28, linewidths=0)
    lims = [min(y.min(), pred.min()), max(y.max(), pred.max())]
    ax.plot(lims, lims, color=RED, linewidth=1.6, linestyle="--", label="Ideal (y = x)")
    ax.set_xlabel("Actual power (kW)")
    ax.set_ylabel("Predicted power (kW)")
    ax.set_title("Actual vs Predicted Power")
    ax.grid(True, **GRID)
    ax.legend(loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_actual_pred.png")


def regime_plot():
    regime = pd.read_csv(ROOT / "outputs" / "metrics" / "regime_errors.csv")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = np.arange(len(regime))
    width = 0.36
    ax.bar(x - width / 2, regime["RMSE"], width, color=TEAL, label="RMSE (kW)")
    ax.bar(x + width / 2, regime["MAE"], width, color=ORANGE, label="MAE (kW)")
    for i, (rmse, mae) in enumerate(zip(regime["RMSE"], regime["MAE"])):
        ax.text(i - width / 2, rmse + 3, f"{rmse:.1f}", ha="center", va="bottom", fontsize=8.5)
        ax.text(i + width / 2, mae + 3, f"{mae:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(regime["Regime"])
    ax.set_ylabel("Error (kW)")
    ax.set_title("Error by Operating Regime (Out-of-Fold, Best Model)")
    ax.legend()
    ax.grid(True, axis="y", **GRID)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_regime_errors.png")


def cleaning_plot(raw, cleaned):
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.9), sharey=True)
    raw_sample = raw.sample(min(6000, len(raw)), random_state=42)
    clean_sample = cleaned.sample(min(6000, len(cleaned)), random_state=42)
    axes[0].scatter(raw_sample["wind_speed"], raw_sample["power"], s=5, color=RED, alpha=0.22, linewidths=0)
    axes[0].set_title(f"Raw Data ({len(raw):,} rows)")
    axes[1].scatter(clean_sample["wind_speed"], clean_sample["power"], s=5, color=TEAL, alpha=0.22, linewidths=0)
    axes[1].set_title(f"Cleaned Data ({len(cleaned):,} rows)")
    for ax in axes:
        ax.set_xlabel("Wind speed (m/s)")
        ax.set_xlim(0, 26)
        ax.set_ylim(-100, 3800)
        ax.grid(True, **GRID)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Active power (kW)")
    fig.suptitle("Effect of Outlier Cleaning on the Operating Envelope", fontweight="bold")
    fig.tight_layout()
    save(fig, "fig_cleaning.png")


def outlier_plot():
    summary = pd.read_csv(ROOT / "outputs" / "metrics" / "outlier_summary.csv")
    summary = summary[summary["Rule"] != "Total removed"].copy()
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    colors = [RED, GOLD, ORANGE, PURPLE, BLUE]
    bars = ax.barh(summary["Rule"], summary["Flagged"], color=colors, alpha=0.8)
    for bar, value in zip(bars, summary["Flagged"]):
        ax.text(value + 40, bar.get_y() + bar.get_height() / 2, f"{int(value):,}", va="center", fontsize=9)
    ax.set_xlabel("Observations flagged")
    ax.set_title("Outlier Rules and Flagged Observations")
    ax.invert_yaxis()
    ax.grid(True, axis="x", **GRID)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "fig_outliers.png")


def main():
    raw = load_data(DATA_PATH)
    params = derive_physical_parameters(raw)
    cleaned, flags, summary = clean_data(
        raw,
        cut_in=params["cut_in"],
        rated_power=params["rated_power"],
    )
    print("rows", len(raw), "cleaned", len(cleaned), "params", params)

    block_diagram()
    cleaning_plot(raw, cleaned)
    outlier_plot()
    models = build_models(params)
    best = models["Hybrid physical spline"]
    X = cleaned[["wind_speed"]].to_numpy(dtype=float)
    y = cleaned["power"].to_numpy(dtype=float)
    best.fit(X, y)
    power_curve(cleaned, best, params)
    model_comparison(cleaned, params)
    cv_boxplot()
    diagnostics(cleaned, params)
    regime_plot()
    print("all figures written to", OUT)


if __name__ == "__main__":
    main()
