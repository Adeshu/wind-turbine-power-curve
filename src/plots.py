import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from sklearn.preprocessing import SplineTransformer
from plotly.subplots import make_subplots

from src.config import WIND_LOWER, WIND_UPPER
from src.models import build_models


COLORS = [
    "#0F766E",
    "#F97316",
    "#2563EB",
    "#DC2626",
    "#7C3AED",
    "#CA8A04",
    "#0891B2",
    "#BE185D",
]


def _sample_frame(df: pd.DataFrame, max_points: int, seed: int = 42):
    if len(df) <= max_points:
        return df
    return df.sample(max_points, random_state=seed)


def _add_vertical_marker(fig, x, label, color="#334155"):
    fig.add_shape(
        type="line",
        x0=x,
        x1=x,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color=color, width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=x,
        y=1.02,
        yref="paper",
        text=label,
        showarrow=False,
        font=dict(size=11, color=color),
        xanchor="center",
    )


def power_curve_figure(
    df: pd.DataFrame,
    model,
    params: dict,
    title: str,
    max_points: int = 6000,
) -> go.Figure:
    sample = _sample_frame(df, max_points)
    grid = np.linspace(WIND_LOWER, WIND_UPPER, 600).reshape(-1, 1)
    predictions = model.predict(grid)

    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=sample["wind_speed"],
            y=sample["power"],
            mode="markers",
            name="Observed",
            marker=dict(size=4, color="#94A3B8", opacity=0.35),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grid.ravel(),
            y=predictions,
            mode="lines",
            name=title,
            line=dict(color="#0F766E", width=3),
        )
    )
    _add_vertical_marker(fig, params["cut_in"], f"Cut-in {params['cut_in']:.1f} m/s")
    _add_vertical_marker(fig, params["rated"], f"Rated {params['rated']:.1f} m/s")

    fig.update_layout(
        template="plotly_white",
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_title="Wind speed (m/s)",
        yaxis_title="Active power (kW)",
        legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig


def model_comparison_curve_figure(
    df: pd.DataFrame,
    params: dict,
    selected_models: list[str] | None = None,
    max_points: int = 5000,
) -> go.Figure:
    sample = _sample_frame(df, max_points)
    grid = np.linspace(WIND_LOWER, WIND_UPPER, 600).reshape(-1, 1)
    models = build_models(params)

    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=sample["wind_speed"],
            y=sample["power"],
            mode="markers",
            name="Observed",
            marker=dict(size=4, color="#CBD5E1", opacity=0.35),
        )
    )

    names = selected_models or list(models.keys())
    for index, name in enumerate(names):
        if name not in models:
            continue
        model = models[name]
        model.fit(df[["wind_speed"]].to_numpy(dtype=float), df["power"].to_numpy(dtype=float))
        predictions = model.predict(grid)
        fig.add_trace(
            go.Scatter(
                x=grid.ravel(),
                y=predictions,
                mode="lines",
                name=name,
                line=dict(color=COLORS[index % len(COLORS)], width=2.5),
            )
        )

    _add_vertical_marker(fig, params["cut_in"], f"Cut-in {params['cut_in']:.1f} m/s")
    _add_vertical_marker(fig, params["rated"], f"Rated {params['rated']:.1f} m/s")
    fig.update_layout(
        template="plotly_white",
        height=540,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_title="Wind speed (m/s)",
        yaxis_title="Active power (kW)",
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def cv_boxplot(fold_results: pd.DataFrame) -> go.Figure:
    fig = px.box(
        fold_results,
        x="model",
        y="rmse",
        color="model",
        points="all",
        template="plotly_white",
    )
    fig.update_layout(
        height=460,
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=120),
        xaxis_title="",
        yaxis_title="Fold RMSE (kW)",
        xaxis_tickangle=-20,
    )
    return fig


def residual_vs_fitted(y_true, y_pred, max_points: int = 5000) -> go.Figure:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    residual = y_true - y_pred
    frame = pd.DataFrame({"fitted": y_pred, "residual": residual})
    frame = _sample_frame(frame, max_points)

    fig = px.scatter(
        frame,
        x="fitted",
        y="residual",
        template="plotly_white",
        opacity=0.4,
        labels={"fitted": "Fitted power (kW)", "residual": "Residual (kW)"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#DC2626")
    fig.update_traces(marker=dict(size=4, color="#2563EB"))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def residual_vs_wind(
    wind_speed,
    y_true,
    y_pred,
    max_points: int = 5000,
) -> go.Figure:
    residual = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    frame = pd.DataFrame(
        {"wind_speed": np.asarray(wind_speed, dtype=float).ravel(), "residual": residual}
    )
    frame = _sample_frame(frame, max_points)

    fig = px.scatter(
        frame,
        x="wind_speed",
        y="residual",
        template="plotly_white",
        opacity=0.4,
        labels={"wind_speed": "Wind speed (m/s)", "residual": "Residual (kW)"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#DC2626")
    fig.update_traces(marker=dict(size=4, color="#F97316"))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def residual_histogram(y_true, y_pred) -> go.Figure:
    residual = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    fig = px.histogram(
        x=residual,
        nbins=60,
        template="plotly_white",
        labels={"x": "Residual (kW)", "y": "Count"},
    )
    fig.update_traces(marker_color="#0F766E")
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def qq_plot(y_true, y_pred) -> go.Figure:
    residual = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    (theoretical, ordered), (slope, intercept, _) = stats.probplot(
        residual, dist="norm"
    )
    line_x = np.array([theoretical.min(), theoretical.max()])
    line_y = slope * line_x + intercept

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=theoretical,
            y=ordered,
            mode="markers",
            name="Residual quantiles",
            marker=dict(size=4, color="#2563EB", opacity=0.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            name="Normal reference",
            line=dict(color="#DC2626", width=2),
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Theoretical quantiles",
        yaxis_title="Ordered residuals",
    )
    return fig


def actual_vs_predicted(y_true, y_pred, max_points: int = 5000) -> go.Figure:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    frame = pd.DataFrame({"actual": y_true, "predicted": y_pred})
    frame = _sample_frame(frame, max_points)
    maximum = float(max(np.nanmax(y_true), np.nanmax(y_pred)))

    fig = px.scatter(
        frame,
        x="actual",
        y="predicted",
        template="plotly_white",
        opacity=0.4,
        labels={"actual": "Actual power (kW)", "predicted": "Predicted power (kW)"},
    )
    fig.add_trace(
        go.Scatter(
            x=[0, maximum],
            y=[0, maximum],
            mode="lines",
            name="Perfect prediction",
            line=dict(color="#DC2626", dash="dash"),
        )
    )
    fig.update_traces(marker=dict(size=4, color="#0F766E"), selector=dict(mode="markers"))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def compute_cooks_distance(X, y, params: dict) -> pd.DataFrame:
    x = np.asarray(X, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    knots = np.array(
        [[WIND_LOWER], [params["cut_in"]], [params["rated"]], [WIND_UPPER]],
        dtype=float,
    )
    spline = SplineTransformer(
        knots=knots,
        degree=3,
        include_bias=False,
        extrapolation="linear",
    )
    basis = spline.fit_transform(x)
    design = np.column_stack([np.ones(len(basis)), basis])

    q_matrix, _ = np.linalg.qr(design)
    leverage = np.clip(np.sum(q_matrix**2, axis=1), 0.0, 1.0 - 1e-9)
    coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coefficients
    parameters = design.shape[1]
    mse = float(np.sum(residual**2) / max(len(y) - parameters, 1))
    cooks = (residual**2 / (parameters * mse)) * (
        leverage / (1.0 - leverage) ** 2
    )

    return pd.DataFrame(
        {
            "row": np.arange(len(y)),
            "wind_speed": x.ravel(),
            "power": y,
            "residual": residual,
            "leverage": leverage,
            "cooks_distance": cooks,
        }
    )


def cooks_distance_figure(cooks_df: pd.DataFrame) -> go.Figure:
    threshold = 4.0 / max(len(cooks_df), 1)
    influential = cooks_df["cooks_distance"] > threshold
    frame = cooks_df.copy()
    frame["influential"] = np.where(influential, "Above threshold", "Below threshold")

    fig = px.scatter(
        frame,
        x="row",
        y="cooks_distance",
        color="influential",
        template="plotly_white",
        opacity=0.6,
        color_discrete_map={
            "Above threshold": "#DC2626",
            "Below threshold": "#94A3B8",
        },
        labels={"row": "Observation", "cooks_distance": "Cook's distance"},
    )
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="#F97316",
        annotation_text=f"4/n = {threshold:.4f}",
        annotation_position="top right",
    )
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def cleaning_scatter(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame, max_points: int = 6000) -> go.Figure:
    removed = raw_df.loc[~raw_df["timestamp"].isin(cleaned_df["timestamp"])]
    kept = _sample_frame(cleaned_df, max_points)
    removed_sample = _sample_frame(removed, max_points)

    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=removed_sample["wind_speed"],
            y=removed_sample["power"],
            mode="markers",
            name=f"Removed ({len(removed):,})",
            marker=dict(size=4, color="#DC2626", opacity=0.45),
        )
    )
    fig.add_trace(
        go.Scattergl(
            x=kept["wind_speed"],
            y=kept["power"],
            mode="markers",
            name=f"Kept ({len(cleaned_df):,})",
            marker=dict(size=4, color="#0F766E", opacity=0.3),
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=480,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Wind speed (m/s)",
        yaxis_title="Active power (kW)",
        legend=dict(orientation="h", y=1.08),
    )
    return fig


def time_series_figure(df: pd.DataFrame) -> go.Figure:
    daily = (
        df.set_index("timestamp")[["power", "wind_speed"]]
        .resample("D")
        .mean()
        .reset_index()
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=daily["timestamp"],
            y=daily["power"],
            mode="lines",
            name="Daily mean power",
            line=dict(color="#0F766E", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily["timestamp"],
            y=daily["wind_speed"],
            mode="lines",
            name="Daily mean wind speed",
            line=dict(color="#F97316", width=1.5),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=1.08),
    )
    fig.update_yaxes(title_text="Power (kW)", secondary_y=False)
    fig.update_yaxes(title_text="Wind speed (m/s)", secondary_y=True)
    return fig


def regime_error_figure(regime_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        regime_df,
        x="Regime",
        y="RMSE",
        color="Regime",
        template="plotly_white",
        text="RMSE",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        height=380,
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis_title="RMSE (kW)",
    )
    return fig


def outlier_summary_figure(summary: pd.DataFrame) -> go.Figure:
    frame = summary[summary["Rule"] != "Total removed"].copy()
    fig = px.bar(
        frame,
        x="Rule",
        y="Flagged",
        color="Enabled",
        template="plotly_white",
        text="Flagged",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=30, b=100),
        xaxis_tickangle=-20,
        yaxis_title="Flagged observations",
        xaxis_title="",
    )
    return fig
