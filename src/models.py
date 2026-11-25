import numpy as np
import patsy
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler

from src.config import WIND_LOWER, WIND_UPPER

MODEL_DESCRIPTIONS = {
    "Mean baseline": "Predicts the average power for every wind speed. Reference only.",
    "Linear regression": "Straight-line fit. Fails to capture the S-shape and plateau.",
    "Polynomial (degree 3)": "Global cubic curve. Flexible but can oscillate at the edges.",
    "Piecewise linear (knots at cut-in and rated)": "Linear segments joined at the physical knots.",
    "Cubic B-spline (knots at cut-in and rated)": "Smooth cubic basis with knots at cut-in and rated speed.",
    "Natural cubic spline (knots at cut-in and rated)": "Cubic spline constrained to be linear beyond boundary knots.",
    "Penalized spline (RidgeCV)": "Many spline basis functions with a cross-validated smoothness penalty.",
    "Hybrid physical spline": "Zero below cut-in, spline in the ramp region, rated power above rated speed.",
}


class ClippedRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, estimator, low=0.0, high=3600.0, cut_in=0.0, rated=None):
        self.estimator = estimator
        self.low = low
        self.high = high
        self.cut_in = cut_in
        self.rated = rated

    def fit(self, X, y):
        self.estimator_ = clone(self.estimator)
        self.estimator_.fit(X, y)
        return self

    def predict(self, X):
        x = np.asarray(X, dtype=float).reshape(-1)
        predictions = np.clip(self.estimator_.predict(X), self.low, self.high)
        if self.cut_in > 0:
            predictions[x < self.cut_in] = 0.0
        if self.rated is not None:
            predictions[x >= self.rated] = self.high
        return predictions


class NaturalCubicSplineRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, knots=(3.0, 13.0), lower_bound=0.0, upper_bound=26.0):
        self.knots = knots
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def _design_matrix(self, X):
        x = np.asarray(X, dtype=float).reshape(-1)
        knot_text = ", ".join(f"{float(knot):.6f}" for knot in self.knots)
        formula = (
            f"cr(x, knots=({knot_text}), "
            f"lower_bound={float(self.lower_bound):.6f}, "
            f"upper_bound={float(self.upper_bound):.6f})"
        )
        return patsy.dmatrix(formula, {"x": x}, return_type="dataframe")

    def fit(self, X, y):
        design = self._design_matrix(X)
        self.model_ = LinearRegression(fit_intercept=False)
        self.model_.fit(design, y)
        return self

    def predict(self, X):
        return self.model_.predict(self._design_matrix(X))


class HybridPowerCurveRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, cut_in=3.0, rated=13.0, rated_power=3600.0, n_knots=6):
        self.cut_in = cut_in
        self.rated = rated
        self.rated_power = rated_power
        self.n_knots = n_knots

    def fit(self, X, y):
        x = np.asarray(X, dtype=float).reshape(-1)
        y = np.asarray(y, dtype=float).reshape(-1)
        ramp = (x >= self.cut_in) & (x < self.rated)

        if int(ramp.sum()) < 20:
            self.ramp_model_ = LinearRegression()
            self.ramp_model_.fit(x[ramp].reshape(-1, 1), y[ramp])
        else:
            self.ramp_model_ = Pipeline(
                [
                    (
                        "spline",
                        SplineTransformer(
                            n_knots=self.n_knots,
                            degree=3,
                            include_bias=False,
                            extrapolation="linear",
                        ),
                    ),
                    ("linear", LinearRegression()),
                ]
            )
            self.ramp_model_.fit(x[ramp].reshape(-1, 1), y[ramp])
        return self

    def predict(self, X):
        x = np.asarray(X, dtype=float).reshape(-1)
        predictions = np.full(len(x), float(self.rated_power), dtype=float)
        below = x < self.cut_in
        ramp = (x >= self.cut_in) & (x < self.rated)
        predictions[below] = 0.0
        if ramp.any():
            predictions[ramp] = self.ramp_model_.predict(
                x[ramp].reshape(-1, 1)
            )
        return np.clip(predictions, 0.0, float(self.rated_power))


def _spline_knots(cut_in: float, rated: float) -> np.ndarray:
    return np.array(
        [[WIND_LOWER], [cut_in], [rated], [WIND_UPPER]], dtype=float
    )


def build_models(params: dict) -> dict:
    cut_in = float(params["cut_in"])
    rated = float(params["rated"])
    rated_power = float(params["rated_power"])
    knots = _spline_knots(cut_in, rated)

    cubic_bspline = Pipeline(
        [
            (
                "spline",
                SplineTransformer(
                    knots=knots,
                    degree=3,
                    include_bias=False,
                    extrapolation="linear",
                ),
            ),
            ("linear", LinearRegression()),
        ]
    )

    piecewise_linear = Pipeline(
        [
            (
                "spline",
                SplineTransformer(
                    knots=knots,
                    degree=1,
                    include_bias=False,
                    extrapolation="linear",
                ),
            ),
            ("linear", LinearRegression()),
        ]
    )

    penalized_spline = Pipeline(
        [
            (
                "spline",
                SplineTransformer(
                    n_knots=20,
                    degree=3,
                    include_bias=False,
                    extrapolation="linear",
                ),
            ),
            ("scale", StandardScaler()),
            (
                "ridge",
                RidgeCV(alphas=np.logspace(-3, 4, 30)),
            ),
        ]
    )

    def physical(estimator):
        return ClippedRegressor(
            estimator,
            low=0.0,
            high=rated_power,
            cut_in=cut_in,
            rated=rated,
        )

    models = {
        "Mean baseline": DummyRegressor(strategy="mean"),
        "Linear regression": physical(LinearRegression()),
        "Polynomial (degree 3)": physical(
            Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=3, include_bias=False)),
                    ("linear", LinearRegression()),
                ]
            )
        ),
        "Piecewise linear (knots at cut-in and rated)": physical(
            piecewise_linear
        ),
        "Cubic B-spline (knots at cut-in and rated)": physical(cubic_bspline),
        "Natural cubic spline (knots at cut-in and rated)": physical(
            NaturalCubicSplineRegressor(
                knots=(cut_in, rated),
                lower_bound=WIND_LOWER,
                upper_bound=WIND_UPPER,
            )
        ),
        "Penalized spline (RidgeCV)": physical(penalized_spline),
        "Hybrid physical spline": HybridPowerCurveRegressor(
            cut_in=cut_in,
            rated=rated,
            rated_power=rated_power,
            n_knots=6,
        ),
    }
    return models
