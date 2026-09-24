# src/models/evaluate.py
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    f1_score, precision_score, recall_score,
    classification_report, RocCurveDisplay,
    PrecisionRecallDisplay
)
from sklearn.calibration import calibration_curve  # ← correct module


def evaluate_model(model, X, y, threshold=0.5, model_name="Model"):
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    metrics = {
        "model":     model_name,
        "roc_auc":   round(roc_auc_score(y, y_prob), 4),
        "pr_auc":    round(average_precision_score(y, y_prob), 4),
        "f1":        round(f1_score(y, y_pred), 4),
        "precision": round(precision_score(y, y_pred), 4),
        "recall":    round(recall_score(y, y_pred), 4),
        "threshold": threshold,
    }

    print(f"\n{'='*50}")
    print(f"  {model_name} @ threshold={threshold}")
    print(f"{'='*50}")
    for k, v in metrics.items():
        print(f"  {k:15s}: {v}")
    print(f"\n{classification_report(y, y_pred, target_names=['Retained','Churned'])}")
    return metrics


def plot_roc_pr(model, X, y, model_name="Model", save_path=None):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    RocCurveDisplay.from_estimator(model, X, y, ax=ax1, name=model_name)
    ax1.plot([0,1],[0,1], 'k--', alpha=0.5)
    ax1.set_title(f'ROC Curve — {model_name}')
    PrecisionRecallDisplay.from_estimator(model, X, y, ax=ax2, name=model_name)
    ax2.set_title(f'PR Curve — {model_name}')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120)
    plt.show()


def plot_calibration(model, X, y, model_name="Model", save_path=None):
    y_prob = model.predict_proba(X)[:, 1]
    prob_true, prob_pred = calibration_curve(y, y_prob, n_bins=10)
    plt.figure(figsize=(7, 5))
    plt.plot(prob_pred, prob_true, 's-', label=model_name)
    plt.plot([0,1],[0,1], 'k--', label='Perfect calibration')
    plt.xlabel('Mean predicted probability')
    plt.ylabel('Fraction of positives')
    plt.title(f'Calibration Curve — {model_name}')
    plt.legend()
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120)
    plt.show()


def tune_threshold(model, X_val, y_val):
    y_prob = model.predict_proba(X_val)[:, 1]
    best_f1, best_threshold = 0, 0.5
    for t in np.arange(0.1, 0.9, 0.01):
        y_pred = (y_prob >= t).astype(int)
        f1 = f1_score(y_val, y_pred)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = t
    print(f"Best threshold: {best_threshold:.2f} | Best F1: {best_f1:.4f}")
    return best_threshold