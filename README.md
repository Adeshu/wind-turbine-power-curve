# Wind Turbine Power Curve Modelling Using Spline Regression

**Student:** Adesh U  
**USN:** 1DB23AD002  
**Subject:** Statistical Machine Learning  
**Syllabus module:** Module 4 — Resampling Methods  
**SDG:** SDG 7 — Affordable and Clean Energy  
**Project No.:** 32

---

## 1. Project overview

Wind turbine output does **not** increase linearly with wind speed. It stays near zero below the cut-in speed, rises steeply through the ramp region, and then flattens at rated power. A straight-line model therefore gives misleading forecasts to grid operators.

This project models the turbine power curve with **spline regression**. The spline knots are placed at the two physically meaningful speeds:

- **Cut-in speed** — the wind speed at which the turbine starts producing power.
- **Rated speed** — the wind speed at which the turbine reaches its rated power.

The project also compares models with **K-fold cross-validation**, removes physically invalid and statistically extreme observations, and provides **diagnostic plots** for the selected model.

A Streamlit frontend makes the complete analysis interactive.

---

## 2. Required outcomes and where they are implemented

| Requirement | Implementation |
|---|---|
| Fitted curves with knots at cut-in and rated speeds | `Power curve` tab, `src/models.py`, `src/plots.py` |
| Cross-validated error comparison | `Model comparison` tab, `src/evaluation.py`, `outputs/metrics/` |
| Diagnostic plots and outlier handling | `Cleaning & outliers` and `Diagnostics` tabs, `src/plots.py` |

---

## 3. Dataset

The project uses `T1.csv`, a 10-minute SCADA dataset from a wind turbine in 2018.

| Column | Use |
|---|---|
| `Date/Time` | Timestamp, used for ordering and time-series checks |
| `LV ActivePower (kW)` | Target variable |
| `Wind Speed (m/s)` | Input feature |
| `Theoretical_Power_Curve (KWh)` | Physical reference for knot detection and outlier checks |
| `Wind Direction (°)` | Displayed in the data summary; not used as a model feature |

The theoretical power curve is **not** used as an input feature. It is effectively a deterministic function of wind speed, so using it as a feature would leak the answer.

Default data facts:

- 50,530 rows, no missing values in the five main columns.
- Wind speed range: 0.0 to 25.2 m/s.
- Active power range: -2.47 to 3,618.7 kW.
- Detected cut-in speed: **3.00 m/s**.
- Detected rated speed: **13.00 m/s**.
- Rated power: **3,600 kW**.

---

## 4. Methodology

### 4.1 Spline regression

A spline represents the power curve as a weighted sum of local basis functions:

```text
power = β0 + β1 B1(wind_speed) + β2 B2(wind_speed) + ... + βp Bp(wind_speed) + error
```

The basis functions are cubic polynomials joined smoothly at the knots. This gives the model enough flexibility to capture the S-shape and the plateau without fitting a separate curve for every wind-speed value.

### 4.2 Knots at cut-in and rated speed

The knots are derived from the theoretical power curve:

- **Cut-in:** first wind speed where theoretical power is positive.
- **Rated:** first wind speed where theoretical power reaches its maximum.
- Additional boundary knots at 0 and 26 m/s keep the spline stable over the observed range.

The sidebar lets the user override both knots for experimentation.

### 4.3 Models compared

| Model | Purpose |
|---|---|
| Mean baseline | Lower-bound reference |
| Linear regression | Shows why a straight line fails |
| Polynomial (degree 3) | Simple global non-linear baseline |
| Piecewise linear with knots | Interpretable segmented fit |
| Cubic B-spline with knots | Main spline model |
| Natural cubic spline with knots | Alternative spline basis |
| Penalized spline with RidgeCV | Smoothness selected by cross-validation |
| Hybrid physical spline | Zero below cut-in, spline in ramp, constant above rated |

All predictions are clipped to the physical operating envelope: `0` below cut-in, the fitted value in the ramp region, and `rated_power` at and above rated speed.

### 4.4 Outlier handling

The app exposes each rule as a toggle:

1. **Negative power** — measurement error.
2. **Power above the rated limit** — measurement spike or scaling error.
3. **Zero power above cut-in** — turbine downtime, curtailment, or de-rating.
4. **Underperformance against the theoretical curve** — sustained de-rated operation.
5. **MAD rule within each 0.5 m/s wind-speed bin** — removes extreme scatter using a robust median absolute deviation rule.

Genuine zero-power readings below cut-in are retained because they are physically valid.

### 4.5 Cross-validation

The default is **5-fold shuffled K-fold cross-validation** with a fixed random seed.

- The spline basis is fitted **inside each training fold**, so the validation fold is never seen during fitting.
- Each model is cloned and refitted for every fold.
- Reported metrics are the mean and standard deviation across folds.
- `train.py` also runs a chronological `TimeSeriesSplit` as a robustness check.

Metrics:

- **RMSE** — primary comparison metric, in kW.
- **MAE** — average absolute error, less sensitive to large residuals.
- **R²** — proportion of variance explained.
- **sMAPE / MAPE** — percentage-style errors; MAPE excludes near-zero power rows.

---

## 5. Default results

The following results are from the default settings in `train.py`:

- 44,306 rows retained after cleaning.
- 6,224 rows removed (12.3%).
- Knots: cut-in = 3.00 m/s, rated = 13.00 m/s.
- 5-fold cross-validation.

| Rank | Model | CV RMSE (kW) | CV MAE (kW) | CV R² |
|---:|---|---:|---:|---:|
| 1 | Hybrid physical spline | **103.89** | **63.38** | 0.9935 |
| 2 | Penalized spline (RidgeCV) | 103.91 | 63.40 | 0.9935 |
| 3 | Cubic B-spline with knots | 110.79 | 72.67 | 0.9927 |
| 4 | Natural cubic spline with knots | 118.79 | 77.28 | 0.9916 |
| 5 | Polynomial (degree 3) | 147.74 | 99.56 | 0.9869 |
| 6 | Piecewise linear with knots | 168.95 | 120.40 | 0.9829 |
| 7 | Linear regression | 313.63 | 237.62 | 0.9411 |
| 8 | Mean baseline | 1,292.70 | 1,140.51 | -0.0002 |

The key result is that spline models reduce cross-validated RMSE by roughly **67%** compared with linear regression. The hybrid physical spline is the best model by a small margin over the penalized spline, while being easier to explain physically.

The exact numbers can change if you modify the cleaning rules, knots, folds, or seed.

### 5.1 Effect of outlier handling

`train.py` also compares each model on the raw data and the cleaned data:

| Model | Raw-data CV RMSE (kW) | Cleaned-data CV RMSE (kW) |
|---|---:|---:|
| Hybrid physical spline | 393.87 | **103.89** |
| Cubic B-spline with knots | 396.38 | 110.79 |
| Linear regression | 487.62 | 313.63 |

Cleaning substantially improves every model, which confirms that downtime and curtailment observations would otherwise dominate the error. The detailed comparison is saved to `outputs/metrics/cleaning_impact.csv`.

---

## 6. Frontend

The Streamlit app has six tabs:

1. **Overview** — dataset summary, time series, distributions, data-quality checks.
2. **Cleaning & outliers** — rule-by-rule counts, before/after scatter, cleaned CSV download.
3. **Power curve** — fitted curve with cut-in and rated markers, plus comparison of all curves.
4. **Model comparison** — CV metrics table, fold-level boxplot, fitted-curve overlay.
5. **Diagnostics** — residuals vs fitted, residuals vs wind speed, histogram, Q-Q plot, actual vs predicted, regime errors, Cook's distance, influential observations.
6. **Methodology** — explanation of the method, module mapping, and limitations.

Sidebar controls let you change:

- Uploaded dataset.
- Cut-in speed, rated speed, and rated power.
- Outlier rules and MAD threshold.
- Number of CV folds and random seed.
- Models included in the comparison.

---

## 7. Project structure

```text
wind-turbine-power-curve/
├── T1.csv                      # raw dataset
├── app.py                      # Streamlit frontend
├── train.py                    # full training + evaluation pipeline
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml             # theme and server settings
├── src/
│   ├── config.py               # constants and folder paths
│   ├── data.py                 # loading, parsing, validation
│   ├── preprocessing.py        # knot detection, cleaning, outlier flags
│   ├── models.py               # spline and baseline estimators
│   ├── evaluation.py           # CV, metrics, regime errors
│   └── plots.py                # Plotly figures
└── outputs/
    ├── metrics/                # CSV and JSON results
    ├── figures/                # interactive HTML figures
    └── models/                 # best_model.joblib
```

---

## 8. How to run the project

### 8.1 Create the virtual environment

Run from the `wind-turbine-power-curve` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `python` is not recognized, use:

```powershell
py -3.10 -m venv .venv
```

### 8.2 Run the training pipeline

```powershell
.\.venv\Scripts\python.exe train.py
```

Optional arguments:

```powershell
.\.venv\Scripts\python.exe train.py --folds 10 --seed 7 --mad-k 2.5
.\.venv\Scripts\python.exe train.py --cut-in 3.0 --rated 13.0 --rated-power 3600
```

This creates:

- `outputs/metrics/model_comparison.csv`
- `outputs/metrics/fold_results.csv`
- `outputs/metrics/time_series_results.csv`
- `outputs/metrics/regime_errors.csv`
- `outputs/metrics/cleaning_impact.csv`
- `outputs/metrics/outlier_summary.csv`
- `outputs/metrics/summary.json`
- `outputs/models/best_model.joblib`
- Interactive HTML figures in `outputs/figures/`

### 8.3 Run the Streamlit app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

If port 8501 is busy:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

### 8.4 PowerShell execution-policy note

If activating the environment is blocked, do **not** change the machine-wide policy. Use the virtual environment's Python executable directly, as shown above. This avoids activation entirely.

---

## 9. Module 4 mapping

Although spline regression is a non-linear modelling technique, the assessment focus is **Module 4: Resampling Methods**:

- K-fold cross-validation for model assessment.
- Bias–variance trade-off.
- Why training error is not a reliable estimate of test error.
- Comparing competing models using out-of-fold predictions.
- Preventing data leakage by fitting the spline basis inside each fold.
- Using a chronological split as a check for time-dependent data.

This connects the spline model to the syllabus requirement rather than treating the project as only a curve-fitting exercise.

---

## 10. Limitations

- The model is univariate: only wind speed is used.
- The model is specific to this turbine and dataset.
- Wind direction, air density, turbulence, and yaw misalignment are not included.
- The dataset does not contain a clear cut-out region, so the curve is treated as constant above rated speed.
- Random K-fold CV ignores temporal dependence; the time-series check in `train.py` partially addresses this.
- Outlier removal improves the fit but can hide genuine curtailment events; the app therefore exposes each rule as a toggle and reports the impact.

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Use `py -3.10 -m venv .venv` |
| `Activate.ps1 cannot be loaded` | Use `.\.venv\Scripts\python.exe` directly |
| Streamlit port already in use | Add `--server.port 8502` |
| Too few rows after cleaning | Uncheck some outlier rules or increase the MAD threshold |
| CSV upload fails | Keep the same five-column order as `T1.csv` |
| First CV run is slow | It is cached; subsequent runs with the same settings are faster |
| Statsmodels/patsy missing | Re-run `pip install -r requirements.txt` inside `.venv` |

---

## 12. Future work

- Add wind direction and air density as features.
- Model the cut-out region explicitly.
- Compare with gradient boosting or random forest as a non-parametric benchmark.
- Use blocked or rolling-origin cross-validation for time-series forecasting.
- Deploy the Streamlit app for a live demonstration.

---

## 13. Acknowledgement

Dataset: `T1.csv`, a public wind turbine SCADA dataset commonly used for power-curve analysis.  
Project prepared for the VTU Statistical Machine Learning course, Module 4.
