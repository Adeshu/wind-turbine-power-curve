from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.base import clone
from sklearn.model_selection import KFold

from src.config import (
    DATA_PATH,
    DEFAULT_MAD_K,
    DEFAULT_OUTLIER_RULES,
    OUTLIER_RULE_LABELS,
)
from src.data import (
    data_quality_summary,
    load_data,
    load_data_from_bytes,
    numeric_summary,
    summary_statistics,
)
from src.evaluation import (
    cv_evaluate,
    cv_summary,
    regime_metrics,
)
from src.models import MODEL_DESCRIPTIONS, build_models
from src.plots import (
    actual_vs_predicted,
    cleaning_scatter,
    compute_cooks_distance,
    cooks_distance_figure,
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
from src.preprocessing import (
    clean_data,
    derive_physical_parameters,
    prepare_xy,
)

st.set_page_config(
    page_title="Wind Turbine Power Curve | SML Project",
    page_icon="W",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetricLabel"] {font-weight: 600; color: #475569;}
    section[data-testid="stSidebar"] {background: #F1F5F9;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_default_data():
    return load_data(DATA_PATH)


@st.cache_data(show_spinner=False)
def cv_cached(
    clean_df: pd.DataFrame,
    model_names: tuple,
    folds: int,
    seed: int,
    cut_in: float,
    rated: float,
    rated_power: float,
):
    params = {
        "cut_in": cut_in,
        "rated": rated,
        "rated_power": rated_power,
    }
    all_models = build_models(params)
    models = {name: all_models[name] for name in model_names}
    X, y = prepare_xy(clean_df)
    cv = KFold(n_splits=folds, shuffle=True, random_state=seed)
    fold_results, oof = cv_evaluate(models, X, y, cv=cv)
    return fold_results, cv_summary(fold_results), oof


@st.cache_data(show_spinner=False)
def single_oof_cached(
    clean_df: pd.DataFrame,
    model_name: str,
    folds: int,
    seed: int,
    cut_in: float,
    rated: float,
    rated_power: float,
):
    params = {
        "cut_in": cut_in,
        "rated": rated,
        "rated_power": rated_power,
    }
    models = {model_name: build_models(params)[model_name]}
    X, y = prepare_xy(clean_df)
    cv = KFold(n_splits=folds, shuffle=True, random_state=seed)
    fold_results, oof = cv_evaluate(models, X, y, cv=cv)
    return fold_results, cv_summary(fold_results), oof


def nice_comparison_table(summary: pd.DataFrame) -> pd.DataFrame:
    table = summary[
        [
            "rank",
            "model",
            "rmse_mean",
            "rmse_std",
            "mae_mean",
            "r2_mean",
            "smape_mean",
        ]
    ].copy()
    table.columns = [
        "Rank",
        "Model",
        "CV RMSE (kW)",
        "RMSE SD",
        "CV MAE (kW)",
        "CV R²",
        "CV sMAPE (%)",
    ]
    return table


def main() -> None:
    st.title("Wind Turbine Power Curve Modelling")
    st.markdown(
        "**Spline regression with knots at cut-in and rated wind speed · SDG 7 — Affordable and Clean Energy**"
    )
    st.caption(
        "Adesh U · USN 1DB23AD002 · Statistical Machine Learning · Module 4 — Resampling Methods"
    )

    st.sidebar.title("Project controls")
    st.sidebar.caption("Dataset: T1.csv · 10-minute SCADA data")

    uploaded = st.sidebar.file_uploader(
        "Upload a CSV (optional)", type=["csv"], help="Leave empty to use T1.csv"
    )
    try:
        if uploaded is not None:
            raw = load_data_from_bytes(uploaded.getvalue())
            source_name = uploaded.name
        else:
            raw = load_default_data()
            source_name = DATA_PATH.name
    except Exception as exc:
        st.error(f"Could not load the dataset: {exc}")
        st.stop()

    detected = derive_physical_parameters(raw)

    st.sidebar.header("Physical parameters")
    cut_in = st.sidebar.number_input(
        "Cut-in wind speed (m/s)",
        min_value=0.0,
        max_value=20.0,
        value=float(detected["cut_in"]),
        step=0.1,
        help="First wind speed where the theoretical power curve becomes positive.",
    )
    rated = st.sidebar.number_input(
        "Rated wind speed (m/s)",
        min_value=cut_in + 0.1,
        max_value=30.0,
        value=max(float(detected["rated"]), cut_in + 0.1),
        step=0.1,
        help="Wind speed where the turbine reaches rated power.",
    )
    rated_power = st.sidebar.number_input(
        "Rated power (kW)",
        min_value=100.0,
        max_value=6000.0,
        value=float(detected["rated_power"]),
        step=10.0,
    )
    params = {
        "cut_in": float(cut_in),
        "rated": float(rated),
        "rated_power": float(rated_power),
        "cut_out": detected["cut_out"],
    }

    st.sidebar.header("Outlier handling")
    rules = {}
    for key, label in OUTLIER_RULE_LABELS.items():
        rules[key] = st.sidebar.checkbox(
            label, value=DEFAULT_OUTLIER_RULES[key]
        )
    mad_k = st.sidebar.slider(
        "MAD threshold (k)",
        min_value=1.0,
        max_value=5.0,
        value=DEFAULT_MAD_K,
        step=0.1,
        help="Observations farther than k robust standard deviations from the wind-bin median are flagged.",
    )

    cleaned, flags, outlier_summary = clean_data(
        raw,
        cut_in=params["cut_in"],
        rated_power=params["rated_power"],
        rules=rules,
        mad_k=mad_k,
    )

    st.sidebar.metric(
        "Rows kept",
        f"{len(cleaned):,}",
        delta=f"-{len(raw) - len(cleaned):,} removed",
    )

    if len(cleaned) < 100:
        st.error("Too few rows remain after cleaning. Relax the outlier rules.")
        st.stop()

    st.sidebar.header("Cross-validation")
    folds = st.sidebar.slider("Number of folds", min_value=3, max_value=10, value=5)
    seed = st.sidebar.number_input("Random seed", min_value=0, max_value=9999, value=42, step=1)
    model_options = list(MODEL_DESCRIPTIONS.keys())
    model_names = st.sidebar.multiselect(
        "Models to compare",
        options=model_options,
        default=model_options,
    )

    config_key = (
        source_name,
        len(cleaned),
        round(float(cleaned["power"].sum()), 4),
        tuple(model_names),
        int(folds),
        int(seed),
        params["cut_in"],
        params["rated"],
        params["rated_power"],
        tuple(sorted(rules.items())),
        float(mad_k),
    )
    if st.session_state.get("_config_key") != config_key:
        st.session_state.pop("cv_results", None)
        st.session_state["_config_key"] = config_key

    overview_tab, cleaning_tab, curve_tab, comparison_tab, diagnostics_tab, methodology_tab = st.tabs(
        [
            "Overview",
            "Cleaning & outliers",
            "Power curve",
            "Model comparison",
            "Diagnostics",
            "Methodology",
        ]
    )

    with overview_tab:
        stats = summary_statistics(raw)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Observations", f"{stats['rows']:,}")
        col2.metric("Wind speed range", f"{stats['wind_min']:.1f} – {stats['wind_max']:.1f} m/s")
        col3.metric("Peak active power", f"{stats['power_max']:,.0f} kW")
        col4.metric("Detected knots", f"{detected['cut_in']:.1f} / {detected['rated']:.1f} m/s")

        st.markdown("#### Data quality")
        left, right = st.columns([1, 1])
        with left:
            st.dataframe(
                data_quality_summary(raw),
                hide_index=True,
                width="stretch",
            )
        with right:
            st.dataframe(
                numeric_summary(raw),
                hide_index=True,
                width="stretch",
            )

        st.markdown("#### Daily operating pattern")
        st.plotly_chart(
            time_series_figure(cleaned),
            width="stretch",
            key="overview_time_series",
        )

        st.markdown("#### Distributions")
        dist_left, dist_right = st.columns(2)
        with dist_left:
            wind_hist = px.histogram(
                cleaned,
                x="wind_speed",
                nbins=60,
                template="plotly_white",
                labels={"wind_speed": "Wind speed (m/s)", "count": "Count"},
                title="Wind speed distribution",
            )
            wind_hist.update_traces(marker_color="#0F766E")
            wind_hist.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(wind_hist, width="stretch", key="wind_histogram")
        with dist_right:
            power_hist = px.histogram(
                cleaned,
                x="power",
                nbins=60,
                template="plotly_white",
                labels={"power": "Active power (kW)", "count": "Count"},
                title="Active power distribution",
            )
            power_hist.update_traces(marker_color="#F97316")
            power_hist.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(power_hist, width="stretch", key="power_histogram")

    with cleaning_tab:
        st.subheader("Outlier handling")
        st.caption(
            f"Raw rows: {len(raw):,} · Cleaned rows: {len(cleaned):,} · "
            f"Removed: {len(raw) - len(cleaned):,} "
            f"({100.0 * (len(raw) - len(cleaned)) / len(raw):.1f}%)"
        )
        st.dataframe(outlier_summary, hide_index=True, width="stretch")
        st.plotly_chart(
            outlier_summary_figure(outlier_summary),
            width="stretch",
            key="outlier_rule_bar",
        )
        st.plotly_chart(
            cleaning_scatter(raw, cleaned),
            width="stretch",
            key="cleaning_scatter_plot",
        )

        st.download_button(
            "Download cleaned data as CSV",
            data=cleaned.to_csv(index=False).encode("utf-8"),
            file_name="T1_cleaned.csv",
            mime="text/csv",
        )

        st.markdown(
            """
            **Why these rules?**
            Negative power and readings above the rated limit are measurement errors.
            Zero power above cut-in usually means the turbine was stopped, curtailed,
            or de-rated. Underperformance against the theoretical curve flags those
            periods. The MAD rule removes extreme scatter within each wind-speed bin
            without deleting the genuine low-wind zeros below cut-in.
            """
        )

    with curve_tab:
        st.subheader("Fitted power curve")
        curve_model_name = st.selectbox(
            "Choose a model to fit on the cleaned data",
            options=model_options,
            index=model_options.index("Cubic B-spline (knots at cut-in and rated)"),
        )
        curve_model = build_models(params)[curve_model_name]
        X_clean, y_clean = prepare_xy(cleaned)
        with st.spinner("Fitting model..."):
            curve_model.fit(X_clean, y_clean)

        st.plotly_chart(
            power_curve_figure(
                cleaned,
                curve_model,
                params,
                title=curve_model_name,
            ),
            width="stretch",
            key="fitted_power_curve",
        )
        st.caption(
            "The dashed vertical lines mark the physical knots: cut-in and rated wind speed. "
            "Predictions are clipped to the physical range 0–rated power."
        )

        with st.expander("Compare all fitted curves"):
            st.plotly_chart(
                model_comparison_curve_figure(
                    cleaned,
                    params,
                    selected_models=model_names or model_options,
                ),
                width="stretch",
                key="curve_tab_model_overlay",
            )

    with comparison_tab:
        st.subheader("Cross-validated model comparison")
        st.caption(
            "Cross-validation is fitted inside each fold. The table reports mean and "
            "standard deviation across folds, so the comparison is not based on a single split."
        )

        if not model_names:
            st.warning("Select at least one model in the sidebar.")
        else:
            run_cv = st.button(
                "Run cross-validation",
                type="primary",
                help="Runs K-fold CV for the selected models and current cleaning settings.",
            )
            if run_cv:
                with st.spinner("Running cross-validation..."):
                    fold_results, summary, oof = cv_cached(
                        cleaned,
                        tuple(model_names),
                        int(folds),
                        int(seed),
                        params["cut_in"],
                        params["rated"],
                        params["rated_power"],
                    )
                st.session_state["cv_results"] = (fold_results, summary, oof)

            if "cv_results" not in st.session_state:
                st.info(
                    "Click **Run cross-validation** to evaluate the selected models. "
                    "The result is cached for the current data and settings."
                )
            else:
                fold_results, summary, oof = st.session_state["cv_results"]
                best = summary.iloc[0]
                metric_cols = st.columns(4)
                metric_cols[0].metric("Best model", best["model"])
                metric_cols[1].metric("CV RMSE", f"{best['rmse_mean']:.1f} kW")
                metric_cols[2].metric("CV MAE", f"{best['mae_mean']:.1f} kW")
                metric_cols[3].metric("CV R²", f"{best['r2_mean']:.4f}")

                table = nice_comparison_table(summary)
                st.dataframe(
                    table.style.format(
                        {
                            "CV RMSE (kW)": "{:.2f}",
                            "RMSE SD": "{:.2f}",
                            "CV MAE (kW)": "{:.2f}",
                            "CV R²": "{:.4f}",
                            "CV sMAPE (%)": "{:.2f}",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.plotly_chart(
                    cv_boxplot(fold_results),
                    width="stretch",
                    key="cv_rmse_boxplot",
                )
                st.plotly_chart(
                    model_comparison_curve_figure(
                        cleaned,
                        params,
                        selected_models=model_names,
                    ),
                    width="stretch",
                    key="comparison_curve_overlay",
                )

                st.download_button(
                    "Download model comparison CSV",
                    data=summary.to_csv(index=False).encode("utf-8"),
                    file_name="model_comparison.csv",
                    mime="text/csv",
                )

    with diagnostics_tab:
        st.subheader("Diagnostic plots")
        cv_exists = "cv_results" in st.session_state
        if cv_exists:
            fold_results, summary, oof = st.session_state["cv_results"]
            default_model = summary.iloc[0]["model"]
            diagnostic_options = list(summary["model"])
        else:
            default_model = "Cubic B-spline (knots at cut-in and rated)"
            diagnostic_options = model_options

        diagnostic_model_name = st.selectbox(
            "Model for diagnostics",
            options=diagnostic_options,
            index=diagnostic_options.index(default_model)
            if default_model in diagnostic_options
            else 0,
            key="diagnostic_model",
        )

        if cv_exists and diagnostic_model_name in oof.columns:
            predictions = oof[diagnostic_model_name].to_numpy(dtype=float)
        else:
            with st.spinner("Generating out-of-fold predictions..."):
                _, _, diagnostic_oof = single_oof_cached(
                    cleaned,
                    diagnostic_model_name,
                    int(folds),
                    int(seed),
                    params["cut_in"],
                    params["rated"],
                    params["rated_power"],
                )
            predictions = diagnostic_oof[diagnostic_model_name].to_numpy(dtype=float)

        X_clean, y_clean = prepare_xy(cleaned)
        wind = cleaned["wind_speed"].to_numpy(dtype=float)

        st.caption(
            "Residuals use out-of-fold predictions, so the diagnostics reflect unseen data."
        )

        residual_tab, distribution_tab, actual_tab, influence_tab = st.tabs(
            ["Residuals", "QQ & distribution", "Actual vs predicted", "Influence"]
        )

        with residual_tab:
            left, right = st.columns(2)
            with left:
                st.plotly_chart(
                    residual_vs_fitted(y_clean, predictions),
                    width="stretch",
                    key="residual_vs_fitted_plot",
                )
            with right:
                st.plotly_chart(
                    residual_vs_wind(wind, y_clean, predictions),
                    width="stretch",
                    key="residual_vs_wind_plot",
                )

        with distribution_tab:
            left, right = st.columns(2)
            with left:
                st.plotly_chart(
                    residual_histogram(y_clean, predictions),
                    width="stretch",
                    key="residual_histogram_plot",
                )
            with right:
                st.plotly_chart(
                    qq_plot(y_clean, predictions),
                    width="stretch",
                    key="residual_qq_plot",
                )

        with actual_tab:
            st.plotly_chart(
                actual_vs_predicted(y_clean, predictions),
                width="stretch",
                key="actual_vs_predicted_plot",
            )
            regime = regime_metrics(
                y_clean,
                predictions,
                wind,
                params["cut_in"],
                params["rated"],
            )
            st.dataframe(
                regime.style.format(
                    {"RMSE": "{:.2f}", "MAE": "{:.2f}", "R2": "{:.4f}"}
                ),
                hide_index=True,
                width="stretch",
            )
            st.plotly_chart(
                regime_error_figure(regime),
                width="stretch",
                key="regime_error_plot",
            )

        with influence_tab:
            cooks = compute_cooks_distance(X_clean, y_clean, params)
            st.plotly_chart(
                cooks_distance_figure(cooks),
                width="stretch",
                key="cooks_distance_plot",
            )
            st.caption(
                "Cook's distance is computed on the cubic B-spline design with knots "
                "at cut-in and rated speed. The dashed line is the common 4/n threshold."
            )
            top_influential = (
                cooks.sort_values("cooks_distance", ascending=False)
                .head(10)
                .loc[:, ["row", "wind_speed", "power", "residual", "leverage", "cooks_distance"]]
            )
            st.dataframe(
                top_influential.style.format(
                    {
                        "wind_speed": "{:.2f}",
                        "power": "{:.1f}",
                        "residual": "{:.1f}",
                        "leverage": "{:.4f}",
                        "cooks_distance": "{:.4f}",
                    }
                ),
                hide_index=True,
                width="stretch",
            )

    with methodology_tab:
        st.subheader("Methodology and module mapping")
        st.markdown(
            f"""
            ### 1. Problem
            A wind turbine's active power rises non-linearly with wind speed and then
            flattens at rated power. A straight-line model misleads grid operators because
            it cannot represent the cut-in region, the steep ramp, or the plateau.

            ### 2. Dataset
            - Source file: `{source_name}`
            - 10-minute SCADA observations from 2018.
            - Target: `LV ActivePower (kW)`.
            - Input: `Wind Speed (m/s)`.
            - `Theoretical_Power_Curve` is used only as a physical reference and for
              outlier checks; it is **not** a model feature, which avoids leakage.

            ### 3. Knots
            The knots are derived from the theoretical power curve:
            - **Cut-in** = first wind speed where theoretical power becomes positive:
              **{detected['cut_in']:.2f} m/s**.
            - **Rated** = first wind speed where theoretical power reaches its maximum:
              **{detected['rated']:.2f} m/s**.
            The sidebar allows you to override both values.

            ### 4. Models
            {chr(10).join(f"- **{name}** — {description}" for name, description in MODEL_DESCRIPTIONS.items())}

            ### 5. Outlier handling
            - Negative power and power above the rated limit are removed as measurement errors.
            - Zero power above cut-in flags downtime or curtailment.
            - Underperformance against the theoretical curve flags de-rated operation.
            - A robust MAD rule removes extreme observations within each 0.5 m/s wind-speed bin.
            Genuine zeros below cut-in are retained.

            ### 6. Cross-validation
            - K-fold cross-validation (default 5 folds) with a fixed random seed.
            - Models are cloned and refitted inside every fold, so the spline basis never
              sees the validation fold.
            - Metrics: RMSE, MAE, R², sMAPE, and MAPE (excluding near-zero power rows).
            - Results are reported as mean ± standard deviation across folds.
            - A chronological `TimeSeriesSplit` is also produced by `train.py` as a
              robustness check.

            ### 7. Module 4 mapping
            This project assesses a non-linear spline model using the **resampling methods**
            from Module 4: K-fold cross-validation, the bias–variance trade-off, model
            comparison, and protection against data leakage.

            ### 8. Limitations
            - The model is univariate and turbine-specific.
            - Wind direction, air density, and yaw misalignment are not modelled.
            - The data has no clear cut-out region, so the plateau is treated as constant.
            - Random K-fold CV ignores temporal dependence; the time-series check in
              `train.py` addresses this partly.

            ### 9. Reproduce the results
            ```powershell
            .\\.venv\\Scripts\\python.exe train.py
            .\\.venv\\Scripts\\python.exe -m streamlit run app.py
            ```
            """
        )

        st.info(
            "Open the `outputs/` folder for saved metrics and interactive HTML figures."
        )


if __name__ == "__main__":
    main()
