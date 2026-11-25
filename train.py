import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import KFold

from src.config import (
    DATA_PATH,
    DEFAULT_CV_FOLDS,
    DEFAULT_MAD_K,
    DEFAULT_OUTLIER_RULES,
    FIGURES_DIR,
    METRICS_DIR,
    MODELS_DIR,
    OUTPUT_DIR,
    RANDOM_STATE,
)
from src.data import data_quality_summary, load_data, summary_statistics
from src.evaluation import (
    cleaning_impact,
    cv_evaluate,
    cv_summary,
    regime_metrics,
    time_series_evaluate,
)
from src.models import build_models
from src.preprocessing import clean_data, derive_physical_parameters
from src.plots import (
    actual_vs_predicted,
    cleaning_scatter,
    cooks_distance_figure,
    compute_cooks_distance,
    cv_boxplot,
    model_comparison_curve_figure,
    outlier_summary_figure,
    power_curve_figure,
    qq_plot,
    regime_error_figure,
    residual_histogram,
    residual_vs_fitted,
    residual_vs_wind,
    time_series_figure,
)


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    return str(value)


def _save_figure(fig, name: str) -> None:
    fig.write_html(FIGURES_DIR / name, include_plotlyjs="cdn")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate wind turbine power curve models."
    )
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--folds", type=int, default=DEFAULT_CV_FOLDS)
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    parser.add_argument("--mad-k", type=float, default=DEFAULT_MAD_K)
    parser.add_argument("--cut-in", type=float, default=None)
    parser.add_argument("--rated", type=float, default=None)
    parser.add_argument("--rated-power", type=float, default=None)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_data(args.data)
    params = derive_physical_parameters(raw)
    if args.cut_in is not None:
        params["cut_in"] = round(float(args.cut_in), 2)
    if args.rated is not None:
        params["rated"] = round(float(args.rated), 2)
    if args.rated_power is not None:
        params["rated_power"] = float(args.rated_power)

    cleaned, flags, outlier_summary = clean_data(
        raw,
        cut_in=params["cut_in"],
        rated_power=params["rated_power"],
        rules=DEFAULT_OUTLIER_RULES,
        mad_k=args.mad_k,
    )

    if len(cleaned) < 100:
        raise RuntimeError("Too few rows remain after cleaning. Check the outlier rules.")

    X = cleaned[["wind_speed"]].to_numpy(dtype=float)
    y = cleaned["power"].to_numpy(dtype=float)

    models = build_models(params)
    cv = KFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    fold_results, oof = cv_evaluate(models, X, y, cv=cv)
    comparison = cv_summary(fold_results)

    best_name = str(comparison.iloc[0]["model"])
    best_model = clone(models[best_name])
    best_model.fit(X, y)

    time_results = time_series_evaluate(
        models, X, y, n_splits=min(args.folds, 5)
    )
    time_summary = (
        time_results.groupby("model", as_index=False)
        .agg(time_rmse=("rmse", "mean"), time_mae=("mae", "mean"), time_r2=("r2", "mean"))
        .sort_values("time_rmse")
    )

    best_oof = oof[best_name].to_numpy(dtype=float)
    regime = regime_metrics(
        y,
        best_oof,
        cleaned["wind_speed"].to_numpy(dtype=float),
        params["cut_in"],
        params["rated"],
    )

    impact_names = [
        "Linear regression",
        "Cubic B-spline (knots at cut-in and rated)",
        "Hybrid physical spline",
    ]
    impact = cleaning_impact(
        raw,
        cleaned,
        params,
        model_names=impact_names,
        folds=args.folds,
        seed=args.seed,
    )

    comparison.to_csv(METRICS_DIR / "model_comparison.csv", index=False)
    fold_results.to_csv(METRICS_DIR / "fold_results.csv", index=False)
    time_results.to_csv(METRICS_DIR / "time_series_results.csv", index=False)
    time_summary.to_csv(METRICS_DIR / "time_series_summary.csv", index=False)
    regime.to_csv(METRICS_DIR / "regime_errors.csv", index=False)
    impact.to_csv(METRICS_DIR / "cleaning_impact.csv", index=False)
    outlier_summary.to_csv(METRICS_DIR / "outlier_summary.csv", index=False)
    data_quality_summary(raw).to_csv(METRICS_DIR / "data_quality.csv", index=False)

    _save_figure(
        power_curve_figure(
            cleaned,
            best_model,
            params,
            title=best_name,
        ),
        "power_curve_best.html",
    )
    _save_figure(
        model_comparison_curve_figure(cleaned, params),
        "model_comparison_curves.html",
    )
    _save_figure(cv_boxplot(fold_results), "cv_boxplot.html")
    _save_figure(
        residual_vs_fitted(y, best_oof),
        "residual_vs_fitted.html",
    )
    _save_figure(
        residual_vs_wind(cleaned["wind_speed"], y, best_oof),
        "residual_vs_wind.html",
    )
    _save_figure(residual_histogram(y, best_oof), "residual_histogram.html")
    _save_figure(qq_plot(y, best_oof), "qq_plot.html")
    _save_figure(actual_vs_predicted(y, best_oof), "actual_vs_predicted.html")
    _save_figure(
        cooks_distance_figure(compute_cooks_distance(X, y, params)),
        "cooks_distance.html",
    )
    _save_figure(cleaning_scatter(raw, cleaned), "cleaning_scatter.html")
    _save_figure(time_series_figure(cleaned), "time_series.html")
    _save_figure(regime_error_figure(regime), "regime_errors.html")
    _save_figure(outlier_summary_figure(outlier_summary), "outlier_summary.html")

    best_metrics = comparison.iloc[0]
    summary = {
        "dataset": summary_statistics(raw),
        "physical_parameters": params,
        "cleaning": {
            "raw_rows": int(len(raw)),
            "cleaned_rows": int(len(cleaned)),
            "removed_rows": int(len(raw) - len(cleaned)),
            "removed_percent": float(100.0 * (len(raw) - len(cleaned)) / len(raw)),
            "mad_k": float(args.mad_k),
        },
        "cross_validation": {
            "folds": int(args.folds),
            "seed": int(args.seed),
            "best_model": best_name,
            "best_rmse": float(best_metrics["rmse_mean"]),
            "best_mae": float(best_metrics["mae_mean"]),
            "best_r2": float(best_metrics["r2_mean"]),
        },
        "models": comparison.to_dict(orient="records"),
        "regime_errors": regime.to_dict(orient="records"),
        "time_series_models": time_summary.to_dict(orient="records"),
    }
    with open(METRICS_DIR / "summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=_json_default)

    joblib.dump(
        {
            "model": best_model,
            "model_name": best_name,
            "params": params,
            "feature": "wind_speed",
        },
        MODELS_DIR / "best_model.joblib",
    )

    print("=" * 72)
    print("WIND TURBINE POWER CURVE MODELLING")
    print("=" * 72)
    print(f"Raw rows      : {len(raw):,}")
    print(f"Cleaned rows  : {len(cleaned):,}")
    print(f"Removed rows  : {len(raw) - len(cleaned):,}")
    print(
        f"Knots         : cut-in = {params['cut_in']:.2f} m/s, "
        f"rated = {params['rated']:.2f} m/s"
    )
    print(f"Rated power   : {params['rated_power']:.0f} kW")
    print("-" * 72)
    print(
        comparison[
            ["rank", "model", "rmse_mean", "mae_mean", "r2_mean"]
        ].to_string(index=False)
    )
    print("-" * 72)
    print(f"Best model    : {best_name}")
    print(f"Outputs       : {OUTPUT_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
