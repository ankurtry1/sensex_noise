from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .ml_dataset import TARGET_CLASS_ORDER

DEFAULT_MODEL_ORDER: tuple[str, ...] = ("logistic", "hgb")
DEFAULT_BINARY_THRESHOLD_GRID = np.round(np.arange(0.10, 0.91, 0.05), 2)
_PROB_EPS = 1e-6


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    fit_dates: tuple[str, ...]
    calibration_dates: tuple[str, ...]
    eval_dates: tuple[str, ...]


@dataclass
class LayerModelResult:
    model_name: str
    predictions: pd.DataFrame
    model_metrics: dict[str, Any]
    threshold_sweep: pd.DataFrame
    confusion_matrix: pd.DataFrame | None
    classification_report: dict[str, Any] | None
    final_model_bundle: dict[str, Any]


@dataclass
class LayerTrainingResult:
    layer_name: str
    feature_mapping: pd.DataFrame
    numeric_features: list[str]
    categorical_features: list[str]
    folds: list[WalkForwardFold]
    model_results: dict[str, LayerModelResult]

    @property
    def model_comparison(self) -> pd.DataFrame:
        rows = [result.model_metrics for result in self.model_results.values()]
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("model").reset_index(drop=True)


def coerce_bool(series: pd.Series) -> pd.Series:
    true_values = {"1", "true", "t", "yes", "y"}
    false_values = {"0", "false", "f", "no", "n", ""}

    def _convert(value: Any) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (int, np.integer)):
            return bool(value)
        if isinstance(value, float):
            if np.isnan(value):
                return False
            return bool(int(value))
        value_str = str(value).strip().lower()
        if value_str in true_values:
            return True
        if value_str in false_values:
            return False
        return False

    return series.map(_convert)


def resolve_feature_columns(
    dataset: pd.DataFrame,
    numeric_candidates: list[str],
    categorical_candidates: list[str],
) -> tuple[list[str], list[str], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    numeric_features: list[str] = []
    categorical_features: list[str] = []

    for feature in numeric_candidates:
        non_null = int(dataset[feature].notna().sum()) if feature in dataset.columns else 0
        status = "used" if feature in dataset.columns and non_null > 0 else "missing_or_no_coverage"
        if status == "used":
            numeric_features.append(feature)
        rows.append(
            {
                "feature": feature,
                "feature_type": "numeric",
                "resolved_column": feature if feature in dataset.columns else "",
                "status": status,
                "non_null_count": non_null,
            }
        )

    for feature in categorical_candidates:
        non_null = int(dataset[feature].notna().sum()) if feature in dataset.columns else 0
        status = "used" if feature in dataset.columns and non_null > 0 else "missing_or_no_coverage"
        if status == "used":
            categorical_features.append(feature)
        rows.append(
            {
                "feature": feature,
                "feature_type": "categorical",
                "resolved_column": feature if feature in dataset.columns else "",
                "status": status,
                "non_null_count": non_null,
            }
        )

    return numeric_features, categorical_features, pd.DataFrame(rows)


def generate_walk_forward_folds(
    dataset: pd.DataFrame,
    *,
    date_col: str = "date",
    eval_start_date: str | None = None,
    min_train_dates: int = 3,
) -> list[WalkForwardFold]:
    if date_col not in dataset.columns:
        return []

    dates = (
        pd.to_datetime(dataset[date_col], errors="coerce")
        .dropna()
        .dt.strftime("%Y-%m-%d")
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    if not dates:
        return []

    eval_start = None if eval_start_date is None else pd.Timestamp(eval_start_date)
    folds: list[WalkForwardFold] = []
    for idx, eval_date in enumerate(dates):
        eval_ts = pd.Timestamp(eval_date)
        if eval_start is not None and eval_ts < eval_start:
            continue
        prior_dates = dates[:idx]
        if len(prior_dates) < min_train_dates:
            continue
        calibration_dates = (prior_dates[-1],)
        fit_dates = tuple(prior_dates[:-1])
        if not fit_dates:
            continue
        folds.append(
            WalkForwardFold(
                fold_id=len(folds) + 1,
                fit_dates=fit_dates,
                calibration_dates=calibration_dates,
                eval_dates=(eval_date,),
            )
        )
    return folds


def _make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
    *,
    scale_numeric: bool,
) -> ColumnTransformer:
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_features:
        numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
        if scale_numeric:
            numeric_steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(numeric_steps), numeric_features))
    if categorical_features:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", _make_one_hot_encoder()),
                    ]
                ),
                categorical_features,
            )
        )
    if not transformers:
        raise ValueError("No usable features remained after schema resolution.")
    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0.0,
        verbose_feature_names_out=False,
    )


def build_estimator(
    model_name: str,
    *,
    numeric_features: list[str],
    categorical_features: list[str],
    problem_type: str,
) -> Pipeline:
    if model_name not in DEFAULT_MODEL_ORDER:
        raise ValueError(f"Unsupported model: {model_name}")

    scale_numeric = model_name == "logistic"
    preprocessor = build_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=scale_numeric,
    )
    if model_name == "logistic":
        solver = "lbfgs"
        model = LogisticRegression(max_iter=2000, solver=solver)
    else:
        model = HistGradientBoostingClassifier(
            loss="log_loss",
            learning_rate=0.05,
            max_depth=3,
            max_iter=250,
            min_samples_leaf=12,
            random_state=42,
        )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def _positive_probability(estimator: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    model = estimator.named_steps["model"]
    probabilities = estimator.predict_proba(frame)
    class_list = list(model.classes_)
    positive_index = class_list.index(1)
    return np.asarray(probabilities[:, positive_index], dtype=float)


def fit_sigmoid_calibrator(probabilities: np.ndarray, labels: pd.Series) -> LogisticRegression | None:
    y = pd.Series(labels).astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        return None
    x = np.clip(probabilities, _PROB_EPS, 1.0 - _PROB_EPS).reshape(-1, 1)
    calibrator = LogisticRegression(max_iter=2000, solver="lbfgs")
    calibrator.fit(x, y)
    return calibrator


def apply_sigmoid_calibrator(
    calibrator: LogisticRegression | None,
    probabilities: np.ndarray,
) -> np.ndarray:
    clipped = np.clip(probabilities, _PROB_EPS, 1.0 - _PROB_EPS).reshape(-1, 1)
    if calibrator is None:
        return clipped[:, 0]
    return np.asarray(calibrator.predict_proba(clipped)[:, 1], dtype=float)


def tune_binary_threshold(
    validation_frame: pd.DataFrame,
    *,
    layer_name: str,
    probability_col: str = "predicted_prob_bad",
    threshold_grid: np.ndarray | None = None,
    min_trade_retention: float = 0.60,
    max_winner_giveback: float = 0.10,
) -> tuple[float, pd.DataFrame]:
    if threshold_grid is None:
        threshold_grid = DEFAULT_BINARY_THRESHOLD_GRID
    frame = validation_frame.copy()
    frame["gross_pnl"] = pd.to_numeric(frame.get("gross_pnl"), errors="coerce").fillna(0.0)
    frame["label_bad_trade"] = pd.to_numeric(frame.get("label_bad_trade"), errors="coerce").fillna(0).astype(int)
    frame["exit_cut_points"] = pd.to_numeric(frame.get("exit_cut_points"), errors="coerce")

    rows: list[dict[str, Any]] = []
    for threshold in threshold_grid:
        if layer_name == "entry_filter":
            accept_mask = frame[probability_col] < threshold
            simulated_pnl = np.where(accept_mask, frame["gross_pnl"], 0.0)
            retained_trade_ratio = float(accept_mask.mean()) if len(frame) else 0.0
            accepted_bad_trade_rate = (
                float(frame.loc[accept_mask, "label_bad_trade"].mean()) if accept_mask.any() else np.nan
            )
            objective_value = float(np.sum(simulated_pnl))
            feasible = retained_trade_ratio >= min_trade_retention
            rows.append(
                {
                    "threshold": threshold,
                    "objective_value": objective_value,
                    "retained_trade_ratio": retained_trade_ratio,
                    "accepted_bad_trade_rate": accepted_bad_trade_rate,
                    "total_policy_pnl": objective_value,
                    "feasible": bool(feasible),
                }
            )
        elif layer_name == "bad_trade_exit":
            exit_mask = frame[probability_col] >= threshold
            simulated_pnl = np.where(
                exit_mask & frame["exit_cut_points"].notna(),
                frame["exit_cut_points"] * 500.0,
                frame["gross_pnl"],
            )
            winners = frame["label_bad_trade"] == 0
            baseline_winner_pnl = float(frame.loc[winners, "gross_pnl"].sum())
            simulated_winner_pnl = float(np.sum(simulated_pnl[winners]))
            winner_giveback = max(baseline_winner_pnl - simulated_winner_pnl, 0.0)
            winner_giveback_ratio = winner_giveback / max(abs(baseline_winner_pnl), 1.0)
            objective_value = float(np.sum(simulated_pnl))
            feasible = winner_giveback_ratio <= max_winner_giveback
            rows.append(
                {
                    "threshold": threshold,
                    "objective_value": objective_value,
                    "winner_giveback_ratio": winner_giveback_ratio,
                    "exit_rate": float(exit_mask.mean()) if len(frame) else 0.0,
                    "total_policy_pnl": objective_value,
                    "feasible": bool(feasible),
                }
            )
        else:
            raise ValueError(f"Unsupported binary threshold layer: {layer_name}")

    sweep = pd.DataFrame(rows)
    if sweep.empty:
        return 0.50, sweep
    feasible = sweep[sweep["feasible"]].copy()
    candidate = feasible if not feasible.empty else sweep.copy()
    if layer_name == "entry_filter":
        candidate = candidate.sort_values(
            ["objective_value", "retained_trade_ratio", "accepted_bad_trade_rate", "threshold"],
            ascending=[False, False, True, True],
        )
    else:
        candidate = candidate.sort_values(
            ["objective_value", "winner_giveback_ratio", "threshold"],
            ascending=[False, True, True],
        )
    best_threshold = float(candidate.iloc[0]["threshold"])
    return best_threshold, sweep


def _extract_feature_names(estimator: Pipeline) -> list[str]:
    preprocessor = estimator.named_steps["preprocessor"]
    if hasattr(preprocessor, "get_feature_names_out"):
        try:
            return list(preprocessor.get_feature_names_out())
        except Exception:
            return []
    return []


def apply_multiclass_fallback(
    frame: pd.DataFrame,
    *,
    fallback_bucket_col: str,
    fallback_confidence: float,
) -> pd.DataFrame:
    scored = frame.copy()
    probability_columns = [column for column in scored.columns if column.startswith("prob_")]
    if not probability_columns:
        raise ValueError("No probability columns found for multiclass fallback.")
    scored["predicted_bucket_raw"] = scored[probability_columns].idxmax(axis=1).str.replace(
        "prob_",
        "",
        regex=False,
    )
    scored["predicted_confidence"] = scored[probability_columns].max(axis=1)
    scored["used_fallback_to_current_bucket"] = scored["predicted_confidence"] < fallback_confidence
    scored["predicted_bucket"] = np.where(
        scored["used_fallback_to_current_bucket"],
        scored[fallback_bucket_col],
        scored["predicted_bucket_raw"],
    )
    return scored


def train_binary_layer(
    dataset: pd.DataFrame,
    *,
    layer_name: str,
    label_col: str,
    numeric_candidates: list[str],
    categorical_candidates: list[str],
    eval_start_date: str | None,
    min_train_dates: int = 3,
    model_order: tuple[str, ...] = DEFAULT_MODEL_ORDER,
) -> LayerTrainingResult:
    frame = dataset.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.loc[frame["date"].notna()].sort_values(["date", "trade_id"]).reset_index(drop=True)
    frame[label_col] = pd.to_numeric(frame[label_col], errors="coerce").fillna(0).astype(int)
    frame["label_bad_trade"] = pd.to_numeric(frame.get("label_bad_trade"), errors="coerce").fillna(0).astype(int)
    numeric_features, categorical_features, feature_mapping = resolve_feature_columns(
        frame,
        numeric_candidates=numeric_candidates,
        categorical_candidates=categorical_candidates,
    )
    folds = generate_walk_forward_folds(
        frame,
        eval_start_date=eval_start_date,
        min_train_dates=min_train_dates,
    )
    if not folds:
        raise ValueError(f"{layer_name}: no walk-forward folds available.")

    model_results: dict[str, LayerModelResult] = {}
    for model_name in model_order:
        eval_predictions: list[pd.DataFrame] = []
        sweep_rows: list[pd.DataFrame] = []
        last_bundle: dict[str, Any] | None = None

        for fold in folds:
            fit_mask = frame["date"].dt.strftime("%Y-%m-%d").isin(fold.fit_dates)
            calibration_mask = frame["date"].dt.strftime("%Y-%m-%d").isin(fold.calibration_dates)
            eval_mask = frame["date"].dt.strftime("%Y-%m-%d").isin(fold.eval_dates)

            fit_df = frame.loc[fit_mask].copy()
            calibration_df = frame.loc[calibration_mask].copy()
            eval_df = frame.loc[eval_mask].copy()
            if fit_df.empty or calibration_df.empty or eval_df.empty:
                continue
            if fit_df[label_col].nunique() < 2:
                continue

            estimator = build_estimator(
                model_name,
                numeric_features=numeric_features,
                categorical_features=categorical_features,
                problem_type="binary",
            )
            selected_columns = numeric_features + categorical_features
            estimator.fit(fit_df[selected_columns], fit_df[label_col])

            calibration_prob = _positive_probability(estimator, calibration_df[selected_columns])
            calibrator = fit_sigmoid_calibrator(calibration_prob, calibration_df[label_col])
            calibration_prob = apply_sigmoid_calibrator(calibrator, calibration_prob)
            validation_frame = calibration_df.copy()
            validation_frame["predicted_prob_bad"] = calibration_prob
            validation_frame["exit_cut_points"] = pd.to_numeric(
                validation_frame.get("exit_cut_points"), errors="coerce"
            )
            threshold, sweep = tune_binary_threshold(validation_frame, layer_name=layer_name)
            sweep["fold_id"] = fold.fold_id
            sweep["calibration_date"] = fold.calibration_dates[0]
            sweep_rows.append(sweep)

            eval_prob = _positive_probability(estimator, eval_df[selected_columns])
            eval_prob = apply_sigmoid_calibrator(calibrator, eval_prob)
            scored = eval_df.copy()
            scored["fold_id"] = fold.fold_id
            scored["calibration_date"] = fold.calibration_dates[0]
            scored["eval_date"] = fold.eval_dates[0]
            scored["model"] = model_name
            scored["predicted_prob_bad"] = eval_prob
            scored["threshold_used"] = threshold
            scored["predicted_bad_trade"] = (scored["predicted_prob_bad"] >= threshold).astype(int)
            scored["actual_label"] = scored[label_col].astype(int)
            eval_predictions.append(scored)

            last_bundle = {
                "layer_name": layer_name,
                "model_name": model_name,
                "estimator": estimator,
                "calibrator": calibrator,
                "threshold": threshold,
                "numeric_features": numeric_features,
                "categorical_features": categorical_features,
                "feature_names": _extract_feature_names(estimator),
            }

        if not eval_predictions or last_bundle is None:
            raise ValueError(f"{layer_name}: model `{model_name}` produced no evaluation predictions.")

        predictions = pd.concat(eval_predictions, ignore_index=True)
        threshold_sweep = pd.concat(sweep_rows, ignore_index=True) if sweep_rows else pd.DataFrame()
        y_true = predictions["actual_label"].astype(int)
        y_pred = predictions["predicted_bad_trade"].astype(int)
        y_prob = predictions["predicted_prob_bad"].astype(float)

        try:
            pr_auc = average_precision_score(y_true, y_prob)
        except ValueError:
            pr_auc = np.nan

        confusion = pd.DataFrame(
            confusion_matrix(y_true, y_pred, labels=[0, 1]),
            index=pd.Index(["actual_not_bad", "actual_bad"], name="actual"),
            columns=pd.Index(["pred_not_bad", "pred_bad"], name="predicted"),
        )
        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        model_results[model_name] = LayerModelResult(
            model_name=model_name,
            predictions=predictions,
            model_metrics={
                "model": model_name,
                "eval_rows": int(len(predictions)),
                "eval_days": int(predictions["eval_date"].nunique()),
                "accuracy": accuracy_score(y_true, y_pred),
                "precision_bad": precision_score(y_true, y_pred, zero_division=0),
                "recall_bad": recall_score(y_true, y_pred, zero_division=0),
                "f1_bad": f1_score(y_true, y_pred, zero_division=0),
                "pr_auc_bad": pr_auc,
                "mean_threshold": float(predictions["threshold_used"].mean()),
            },
            threshold_sweep=threshold_sweep,
            confusion_matrix=confusion,
            classification_report=report,
            final_model_bundle=last_bundle,
        )

    return LayerTrainingResult(
        layer_name=layer_name,
        feature_mapping=feature_mapping,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        folds=folds,
        model_results=model_results,
    )


def train_multiclass_layer(
    dataset: pd.DataFrame,
    *,
    layer_name: str,
    label_col: str,
    numeric_candidates: list[str],
    categorical_candidates: list[str],
    eval_start_date: str | None,
    min_train_dates: int = 3,
    model_order: tuple[str, ...] = DEFAULT_MODEL_ORDER,
    fallback_bucket_col: str = "current_bucket",
    fallback_confidence: float = 0.55,
) -> LayerTrainingResult:
    frame = dataset.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.loc[frame["date"].notna()].sort_values(["date", "trade_id"]).reset_index(drop=True)
    frame = frame.loc[frame[label_col].isin(TARGET_CLASS_ORDER)].copy()
    numeric_features, categorical_features, feature_mapping = resolve_feature_columns(
        frame,
        numeric_candidates=numeric_candidates,
        categorical_candidates=categorical_candidates,
    )
    folds = generate_walk_forward_folds(
        frame,
        eval_start_date=eval_start_date,
        min_train_dates=min_train_dates,
    )
    if not folds:
        raise ValueError(f"{layer_name}: no walk-forward folds available.")

    model_results: dict[str, LayerModelResult] = {}
    selected_columns = numeric_features + categorical_features
    for model_name in model_order:
        eval_predictions: list[pd.DataFrame] = []
        last_bundle: dict[str, Any] | None = None

        for fold in folds:
            train_dates = tuple(list(fold.fit_dates) + list(fold.calibration_dates))
            train_mask = frame["date"].dt.strftime("%Y-%m-%d").isin(train_dates)
            eval_mask = frame["date"].dt.strftime("%Y-%m-%d").isin(fold.eval_dates)
            train_df = frame.loc[train_mask].copy()
            eval_df = frame.loc[eval_mask].copy()
            if train_df.empty or eval_df.empty:
                continue
            if train_df[label_col].nunique() < 2:
                continue

            estimator = build_estimator(
                model_name,
                numeric_features=numeric_features,
                categorical_features=categorical_features,
                problem_type="multiclass",
            )
            estimator.fit(train_df[selected_columns], train_df[label_col])
            probabilities = pd.DataFrame(
                estimator.predict_proba(eval_df[selected_columns]),
                index=eval_df.index,
                columns=[f"prob_{label}" for label in estimator.named_steps["model"].classes_],
            )
            scored = eval_df.copy()
            scored["fold_id"] = fold.fold_id
            scored["eval_date"] = fold.eval_dates[0]
            scored["model"] = model_name
            for label in TARGET_CLASS_ORDER:
                scored[f"prob_{label}"] = probabilities.get(f"prob_{label}", np.nan)
            scored = apply_multiclass_fallback(
                scored,
                fallback_bucket_col=fallback_bucket_col,
                fallback_confidence=fallback_confidence,
            )
            scored["actual_label"] = scored[label_col]
            eval_predictions.append(scored)

            last_bundle = {
                "layer_name": layer_name,
                "model_name": model_name,
                "estimator": estimator,
                "fallback_confidence": fallback_confidence,
                "numeric_features": numeric_features,
                "categorical_features": categorical_features,
                "feature_names": _extract_feature_names(estimator),
            }

        if not eval_predictions or last_bundle is None:
            raise ValueError(f"{layer_name}: model `{model_name}` produced no evaluation predictions.")

        predictions = pd.concat(eval_predictions, ignore_index=True)
        y_true = predictions["actual_label"]
        y_pred = predictions["predicted_bucket"]
        confusion = pd.DataFrame(
            confusion_matrix(y_true, y_pred, labels=TARGET_CLASS_ORDER),
            index=pd.Index(TARGET_CLASS_ORDER, name="actual"),
            columns=pd.Index(TARGET_CLASS_ORDER, name="predicted"),
        )
        report = classification_report(
            y_true,
            y_pred,
            labels=TARGET_CLASS_ORDER,
            output_dict=True,
            zero_division=0,
        )
        model_results[model_name] = LayerModelResult(
            model_name=model_name,
            predictions=predictions,
            model_metrics={
                "model": model_name,
                "eval_rows": int(len(predictions)),
                "eval_days": int(predictions["eval_date"].nunique()),
                "accuracy": accuracy_score(y_true, y_pred),
                "macro_f1": f1_score(y_true, y_pred, labels=TARGET_CLASS_ORDER, average="macro", zero_division=0),
                "weighted_f1": f1_score(
                    y_true,
                    y_pred,
                    labels=TARGET_CLASS_ORDER,
                    average="weighted",
                    zero_division=0,
                ),
                "fallback_rate": float(predictions["used_fallback_to_current_bucket"].mean()),
            },
            threshold_sweep=pd.DataFrame(),
            confusion_matrix=confusion,
            classification_report=report,
            final_model_bundle=last_bundle,
        )

    return LayerTrainingResult(
        layer_name=layer_name,
        feature_mapping=feature_mapping,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        folds=folds,
        model_results=model_results,
    )


def save_model_bundle(bundle: dict[str, Any], path: Path) -> None:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
