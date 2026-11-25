import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, TimeSeriesSplit

from src.config import DEFAULT_CV_FOLDS, RANDOM_STATE
from src.models import build_models


def _as_2d(X) -> np.ndarray:
    if isinstance(X, pd.DataFrame):
        return X.to_numpy(dtype=float)
    array = np.asarray(X, dtype=float)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    return array


def _as_1d(y) -> np.ndarray:
    return np.asarray(y, dtype=float).reshape(-1)


def regression_metrics(y_true, y_pred) -> dict:
    y_true = _as_1d(y_true)
    y_pred = _as_1d(y_pred)
    residual = y_true - y_pred

    rmse = float(np.sqrt(np.mean(residual**2)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else np.nan

    denominator = np.abs(y_true) + np.abs(y_pred) + 1e-9
    smape = float(100.0 * np.mean(2.0 * np.abs(residual) / denominator))

    non_zero = np.abs(y_true) > 1.0
    if non_zero.any():
        mape = float(
            100.0
            * np.mean(
                np.abs(residual[non_zero]) / np.abs(y_true[non_zero])
            )
        )
    else:
        mape = np.nan

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "smape": smape,
        "mape": mape,
    }


def cv_evaluate(
    models: dict,
    X,
    y,
    cv=None,
    collect_oof: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    X = _as_2d(X)
    y = _as_1d(y)
    if cv is None:
        cv = KFold(
            n_splits=DEFAULT_CV_FOLDS,
            shuffle=True,
            random_state=RANDOM_STATE,
        )

    records = []
    oof = (
        pd.DataFrame(
            index=np.arange(len(y)),
            columns=list(models.keys()),
            dtype=float,
        )
        if collect_oof
        else pd.DataFrame()
    )

    splits = list(cv.split(X, y))
    for model_name, estimator in models.items():
        for fold, (train_index, test_index) in enumerate(splits, start=1):
            model = clone(estimator)
            model.fit(X[train_index], y[train_index])
            predictions = model.predict(X[test_index])
            records.append(
                {
                    "model": model_name,
                    "fold": fold,
                    **regression_metrics(y[test_index], predictions),
                }
            )
            if collect_oof:
                oof.loc[test_index, model_name] = predictions

    return pd.DataFrame(records), oof


def cv_summary(fold_results: pd.DataFrame) -> pd.DataFrame:
    summary = (
        fold_results.groupby("model")
        .agg(
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
            smape_mean=("smape", "mean"),
            mape_mean=("mape", "mean"),
        )
        .reset_index()
    )
    summary[["rmse_std", "mae_std", "r2_std"]] = summary[
        ["rmse_std", "mae_std", "r2_std"]
    ].fillna(0.0)
    summary = summary.sort_values("rmse_mean").reset_index(drop=True)
    summary.insert(0, "rank", np.arange(1, len(summary) + 1))
    return summary


def time_series_evaluate(
    models: dict,
    X,
    y,
    n_splits: int = DEFAULT_CV_FOLDS,
) -> pd.DataFrame:
    X = _as_2d(X)
    y = _as_1d(y)
    cv = TimeSeriesSplit(n_splits=n_splits)
    records = []

    for model_name, estimator in models.items():
        for fold, (train_index, test_index) in enumerate(cv.split(X), start=1):
            model = clone(estimator)
            model.fit(X[train_index], y[train_index])
            predictions = model.predict(X[test_index])
            records.append(
                {
                    "model": model_name,
                    "fold": fold,
                    **regression_metrics(y[test_index], predictions),
                }
            )
    return pd.DataFrame(records)


def regime_metrics(
    y_true,
    y_pred,
    wind_speed,
    cut_in: float,
    rated: float,
) -> pd.DataFrame:
    y_true = _as_1d(y_true)
    y_pred = _as_1d(y_pred)
    wind = _as_1d(wind_speed)

    regimes = np.select(
        [wind < cut_in, wind < rated],
        ["Below cut-in", "Ramp region"],
        default="Rated region",
    )

    rows = []
    for regime in ["Below cut-in", "Ramp region", "Rated region"]:
        mask = regimes == regime
        if not mask.any():
            continue
        metrics = regression_metrics(y_true[mask], y_pred[mask])
        rows.append(
            {
                "Regime": regime,
                "Samples": int(mask.sum()),
                "RMSE": metrics["rmse"],
                "MAE": metrics["mae"],
                "R2": metrics["r2"],
            }
        )
    return pd.DataFrame(rows)


def cleaning_impact(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    params: dict,
    model_names: list[str],
    folds: int = DEFAULT_CV_FOLDS,
    seed: int = RANDOM_STATE,
) -> pd.DataFrame:
    all_models = build_models(params)
    selected_models = {
        name: all_models[name] for name in model_names if name in all_models
    }
    cv = KFold(n_splits=folds, shuffle=True, random_state=seed)

    outputs = []
    for label, data in [("Raw data", raw_df), ("Cleaned data", cleaned_df)]:
        X = data[["wind_speed"]].to_numpy(dtype=float)
        y = data["power"].to_numpy(dtype=float)
        fold_results, _ = cv_evaluate(
            selected_models, X, y, cv=cv, collect_oof=False
        )
        summary = cv_summary(fold_results)
        summary["Dataset"] = label
        summary["Samples"] = len(data)
        outputs.append(summary)

    return pd.concat(outputs, ignore_index=True)
