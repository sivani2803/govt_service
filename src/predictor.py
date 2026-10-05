from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from catboost import CatBoostClassifier, CatBoostError

from src.config import FEATURE_MEDIANS_PATH, PRIORITY_MODEL_PATH, PROJECT_CONFIG_PATH


@st.cache_resource(show_spinner="Loading local priority model...")
def load_predictor_assets() -> tuple[CatBoostClassifier, dict[str, Any], dict[str, float]]:
    for path in (PRIORITY_MODEL_PATH, PROJECT_CONFIG_PATH, FEATURE_MEDIANS_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required model artifact does not exist: {path}")

    try:
        with PROJECT_CONFIG_PATH.open("rb") as config_file:
            project_config = pickle.load(config_file)
        with FEATURE_MEDIANS_PATH.open("rb") as medians_file:
            feature_medians = pickle.load(medians_file)
    except (pickle.PickleError, EOFError) as exc:
        raise RuntimeError(f"A saved model support artifact could not be read: {exc}") from exc

    if not isinstance(project_config, dict) or not isinstance(feature_medians, dict):
        raise ValueError("The saved project configuration or feature medians have an unexpected format.")
    if not project_config.get("feature_cols"):
        raise ValueError("The saved project configuration does not define feature_cols.")
    if "high_threshold" not in project_config:
        raise ValueError("The saved project configuration does not define high_threshold.")

    model = CatBoostClassifier()
    try:
        model.load_model(str(PRIORITY_MODEL_PATH))
    except (OSError, ValueError, CatBoostError) as exc:
        raise RuntimeError(f"CatBoost could not load the saved model: {exc}") from exc
    if list(model.feature_names_) != list(project_config["feature_cols"]):
        raise ValueError("Saved model features do not match project_config.pkl.")
    return model, project_config, feature_medians


def build_model_row(
    project_config: dict[str, Any],
    feature_medians: dict[str, float],
    complaint: dict[str, Any],
) -> pd.DataFrame:
    now = datetime.now()
    values: dict[str, Any] = {
        **complaint,
        "LATITUDE": complaint.get("LATITUDE")
        if complaint.get("LATITUDE") is not None
        else feature_medians["LATITUDE"],
        "LONGITUDE": complaint.get("LONGITUDE")
        if complaint.get("LONGITUDE") is not None
        else feature_medians["LONGITUDE"],
        "YEAR": complaint.get("YEAR", now.year),
        "ADD_YEAR": complaint.get("ADD_YEAR", now.year),
        "ADD_MONTH": complaint.get("ADD_MONTH", now.month),
        "ADD_DAYOFWEEK": complaint.get("ADD_DAYOFWEEK", now.weekday()),
        "ADD_HOUR": complaint.get("ADD_HOUR", now.hour),
    }
    features = list(project_config["feature_cols"])
    missing = [feature for feature in features if feature not in values]
    if missing:
        raise ValueError(f"Required model inputs are missing: {', '.join(missing)}")
    for column in project_config.get("categorical_features", []):
        values[column] = str(values[column])
    return pd.DataFrame([{feature: values[feature] for feature in features}], columns=features)


def predict_priority(
    model: CatBoostClassifier,
    project_config: dict[str, Any],
    feature_medians: dict[str, float],
    complaint: dict[str, Any],
) -> tuple[str, dict[str, float]]:
    row = build_model_row(project_config, feature_medians, complaint)
    raw_probabilities = model.predict_proba(row)[0]
    probabilities = {
        str(label): float(probability)
        for label, probability in zip(model.classes_, raw_probabilities)
    }
    required_classes = {"High", "Low", "Medium"}
    if not required_classes.issubset(probabilities):
        raise ValueError("The saved priority model does not contain all expected priority classes.")

    if probabilities["High"] >= float(project_config["high_threshold"]):
        priority = "High"
    else:
        priority = max(("Low", "Medium"), key=probabilities.__getitem__)
    return priority, probabilities
