"""
train_evaluate.py
-----------------
Multi-output outreach prediction engine.

Models trained for both channel + tone:
  1. RandomForest          – strong baseline, MDI feature importances
  2. GradientBoosting      – higher accuracy, captures interactions
  3. MLP Neural Network    – non-linear, fast with early stopping
  + HPO on the winner via RandomizedSearchCV (10 iter, 3-fold)

Outputs:
  models/   – serialised best pipelines per target (.joblib)
  results/  – confusion matrices, ROC-AUC curves, feature importance
              plots, experiment_log.csv
"""

import os, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.ensemble        import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network  import MLPClassifier
from sklearn.pipeline        import Pipeline
from sklearn.preprocessing   import LabelEncoder, label_binarize
from sklearn.model_selection import (
    train_test_split, StratifiedKFold,
    RandomizedSearchCV, cross_val_score,
)
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, f1_score,
    roc_curve, auc,
)
from sklearn.inspection import permutation_importance
from scipy.stats import randint

from feature_pipeline import build_preprocessor

warnings.filterwarnings("ignore")

# ── Directory setup ───────────────────────────────────────────────────────────
for d in ("models", "results", "data"):
    os.makedirs(d, exist_ok=True)

# ── Dark theme ────────────────────────────────────────────────────────────────
P = {
    "pri": "#6C3FC5", "sec": "#3D8BF5", "acc": "#F5A623",
    "bg":  "#0D0D0D", "panel": "#1A1A2E", "txt": "#FFFFFF",
}
plt.rcParams.update({
    "figure.facecolor": P["bg"],   "axes.facecolor":  P["panel"],
    "axes.edgecolor":   "#444",    "text.color":      P["txt"],
    "axes.labelcolor":  P["txt"],  "xtick.color":     P["txt"],
    "ytick.color":      P["txt"],  "font.family":     "DejaVu Sans",
    "grid.color":       "#333",    "grid.linestyle":  "--",
    "grid.alpha":       0.4,
})

TARGET_CH = "best_channel"
TARGET_TN = "tone"


# ── Utilities ─────────────────────────────────────────────────────────────────
def encode_targets(df):
    le_ch, le_tn = LabelEncoder(), LabelEncoder()
    return (
        le_ch.fit_transform(df[TARGET_CH]),
        le_tn.fit_transform(df[TARGET_TN]),
        le_ch, le_tn,
    )


def get_model_zoo():
    return {
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=None, min_samples_leaf=2,
            n_jobs=-1, class_weight="balanced", random_state=42,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.08,
            max_depth=5, subsample=0.85, random_state=42,
        ),
        "MLP_NeuralNetwork": MLPClassifier(
            hidden_layer_sizes=(256, 128, 64), activation="relu",
            solver="adam", learning_rate_init=5e-4, max_iter=400,
            early_stopping=True, validation_fraction=0.1,
            n_iter_no_change=15, random_state=42,
        ),
    }


def hpo_on_winner(best_pipe, X_tr, y_tr):
    """10-iter RandomizedSearch on best tree model."""
    clf = best_pipe.named_steps["clf"]
    if isinstance(clf, RandomForestClassifier):
        param_dist = {
            "clf__n_estimators":     randint(150, 400),
            "clf__max_depth":        [None, 10, 20, 30],
            "clf__min_samples_leaf": randint(1, 8),
        }
    elif isinstance(clf, GradientBoostingClassifier):
        param_dist = {
            "clf__n_estimators":  randint(100, 300),
            "clf__learning_rate": [0.03, 0.05, 0.08, 0.12],
            "clf__max_depth":     [3, 4, 5, 6],
        }
    else:
        return best_pipe   # MLP – skip HPO for speed

    print("    [HPO] RandomizedSearchCV (10 iter, 3-fold) ...")
    search = RandomizedSearchCV(
        best_pipe, param_distributions=param_dist,
        n_iter=10,
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
        scoring="f1_weighted", n_jobs=-1, verbose=0, random_state=42,
    )
    search.fit(X_tr, y_tr)
    print(f"    HPO best CV-F1: {search.best_score_:.4f} | params: {search.best_params_}")
    return search.best_estimator_


# ── Main training loop ────────────────────────────────────────────────────────
def train_and_evaluate(df: pd.DataFrame):
    print("=" * 68)
    print("  AI OUTREACH DECISION ENGINE  –  Full Training Pipeline")
    print("=" * 68)

    y_ch, y_tn, le_ch, le_tn = encode_targets(df)
    feat_cols = [c for c in df.columns if c not in [TARGET_CH, TARGET_TN]]
    X = df[feat_cols]

    # 80 / 10 / 10 stratified split
    X_tmp, X_te, y_ch_tmp, y_ch_te, y_tn_tmp, y_tn_te = train_test_split(
        X, y_ch, y_tn, test_size=0.10, stratify=y_ch, random_state=42,
    )
    X_tr, X_va, y_ch_tr, y_ch_va, y_tn_tr, y_tn_va = train_test_split(
        X_tmp, y_ch_tmp, y_tn_tmp,
        test_size=0.111, stratify=y_ch_tmp, random_state=42,
    )
    print(f"  Split  →  Train: {len(X_tr)}  |  Val: {len(X_va)}  |  Test: {len(X_te)}\n")

    log = []

    for tgt, y_tr, y_va, y_te, le in [
        ("channel", y_ch_tr, y_ch_va, y_ch_te, le_ch),
        ("tone",    y_tn_tr, y_tn_va, y_tn_te, le_tn),
    ]:
        print(f"\n{'─'*60}")
        print(f"  TARGET → {tgt.upper()}   classes: {list(le.classes_)}")
        print(f"{'─'*60}")

        best_pipe, best_name, best_f1 = None, "", -1

        for mname, clf in get_model_zoo().items():
            t0 = time.time()
            pipe = Pipeline([
                ("preprocessor", build_preprocessor()),
                ("clf", clf),
            ])
            pipe.fit(X_tr, y_tr)

            cv = cross_val_score(
                pipe, X_tr, y_tr,
                cv=StratifiedKFold(3, shuffle=True, random_state=42),
                scoring="f1_weighted", n_jobs=-1,
            )
            va_preds = pipe.predict(X_va)
            va_f1  = f1_score(y_va, va_preds, average="weighted", zero_division=0)
            va_acc = accuracy_score(y_va, va_preds)
            elapsed = time.time() - t0

            print(f"  [{mname:<20}]  CV: {cv.mean():.4f}±{cv.std():.4f}"
                  f"  |  Val F1: {va_f1:.4f}  Acc: {va_acc:.4f}  |  {elapsed:.1f}s")

            log.append(dict(
                target=tgt, model=mname,
                cv_f1=round(cv.mean(), 4), cv_std=round(cv.std(), 4),
                val_f1=round(va_f1, 4), val_acc=round(va_acc, 4),
                train_sec=round(elapsed, 2),
            ))

            if va_f1 > best_f1:
                best_f1, best_name, best_pipe = va_f1, mname, pipe

        print(f"\n  ★  Best base model: {best_name}  (Val F1 = {best_f1:.4f})")

        # HPO on winner
        best_pipe = hpo_on_winner(best_pipe, X_tr, y_tr)

        # Final test evaluation
        te_preds = best_pipe.predict(X_te)
        report   = classification_report(
            y_te, te_preds, target_names=le.classes_,
            output_dict=True, zero_division=0,
        )
        print(f"\n  ── Test Report ({tgt}) ──")
        print(classification_report(y_te, te_preds, target_names=le.classes_, zero_division=0))

        _plot_cm(y_te, te_preds, le.classes_, tgt, best_name)
        if hasattr(best_pipe, "predict_proba"):
            _plot_roc(best_pipe, X_te, y_te, le.classes_, tgt)
        _plot_importance(best_pipe, X_tr, tgt, best_name)

        # Save artefact
        joblib.dump(
            dict(pipeline=best_pipe, label_encoder=le, feature_cols=feat_cols),
            f"models/best_{tgt}_model.joblib",
        )
        print(f"  Model saved  →  models/best_{tgt}_model.joblib")

        log.append(dict(
            target=tgt, model=f"BEST:{best_name}",
            cv_f1="—", cv_std="—", val_f1="—", val_acc="—",
            train_sec="—",
            test_f1=round(report["weighted avg"]["f1-score"], 4),
            test_acc=round(report["accuracy"], 4),
        ))

    # Experiment log + comparison chart
    log_df = pd.DataFrame(log)
    log_df.to_csv("results/experiment_log.csv", index=False)
    print("\n  Experiment log  →  results/experiment_log.csv")
    _plot_comparison(log_df)

    print("\n" + "=" * 68)
    print("  Pipeline complete.  Artefacts in  models/  and  results/")
    print("=" * 68)


# ── Plot helpers ──────────────────────────────────────────────────────────────

def _plot_cm(y_true, y_pred, classes, tgt, model_name):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Purples",
        xticklabels=classes, yticklabels=classes,
        linewidths=0.4, ax=ax, annot_kws={"size": 9},
    )
    ax.set_title(f"Confusion Matrix — {tgt.upper()}\n({model_name})",
                 fontsize=12, color=P["acc"], pad=10)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    plt.tight_layout()
    plt.savefig(f"results/confusion_{tgt}.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Confusion matrix   →  results/confusion_{tgt}.png")


def _plot_roc(pipe, X_te, y_te, classes, tgt):
    n_cls   = len(classes)
    y_bin   = label_binarize(y_te, classes=range(n_cls))
    y_score = pipe.predict_proba(X_te)

    fig, ax = plt.subplots(figsize=(8, 6))
    colors  = plt.cm.tab10(np.linspace(0, 1, n_cls))
    aucs    = []

    for i, (cls, col) in enumerate(zip(classes, colors)):
        if i >= y_bin.shape[1]:
            break
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_score[:, i])
        ra = auc(fpr, tpr); aucs.append(ra)
        ax.plot(fpr, tpr, color=col, lw=2, label=f"{cls} (AUC={ra:.2f})")

    ax.plot([0, 1], [0, 1], "w--", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(
        f"ROC-AUC Curves — {tgt.upper()}  [macro avg = {np.mean(aucs):.3f}]",
        fontsize=12, color=P["acc"],
    )
    ax.legend(loc="lower right", fontsize=8, framealpha=0.3)
    ax.grid(True); ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    plt.tight_layout()
    plt.savefig(f"results/roc_{tgt}.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ROC-AUC curves     →  results/roc_{tgt}.png")


def _plot_importance(pipe, X_tr, tgt, model_name):
    try:
        clf = pipe.named_steps["clf"]
        pre = pipe.named_steps["preprocessor"]

        try:
            feat_names = pre.get_feature_names_out().tolist()
        except Exception:
            feat_names = [f"f{i}" for i in range(200)]

        if hasattr(clf, "feature_importances_"):
            imp   = clf.feature_importances_
            label = "MDI Feature Importance (mean impurity decrease)"
        else:
            Xt = pre.transform(X_tr)
            res = permutation_importance(
                clf, Xt, clf.predict(Xt),
                n_repeats=5, random_state=42, n_jobs=-1,
            )
            imp        = res.importances_mean
            feat_names = feat_names[:len(imp)]
            label      = "Permutation Importance"

        n   = min(20, len(imp))
        idx = np.argsort(imp)[::-1][:n]
        vals = imp[idx]
        lbls = [
            feat_names[i]
            .replace("num__", "")
            .replace("cat__", "")
            .replace("eng__", "★ ")
            for i in idx
        ]

        fig, ax = plt.subplots(figsize=(10, 7))
        colors  = [P["acc"] if "★" in l else P["pri"] for l in lbls]
        ax.barh(range(n), vals[::-1], color=colors[::-1], height=0.65)
        ax.set_yticks(range(n))
        ax.set_yticklabels(lbls[::-1], fontsize=9)
        ax.set_xlabel("Importance Score", fontsize=11)
        ax.set_title(
            f"{label}\nTarget: {tgt.upper()}  |  Model: {model_name}"
            f"  (★ = engineered feature)",
            fontsize=11, color=P["acc"], pad=10,
        )
        for j, v in enumerate(vals[::-1]):
            ax.text(v + 0.0005, j, f"{v:.4f}", va="center",
                    fontsize=7, color=P["txt"])
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(
            f"results/feature_importance_{tgt}.png",
            dpi=150, bbox_inches="tight",
        )
        plt.close()
        print(f"  Feature importance →  results/feature_importance_{tgt}.png")

    except Exception as e:
        print(f"  [Importance] Skipped: {e}")


def _plot_comparison(log_df: pd.DataFrame):
    rows = log_df[log_df["val_f1"].apply(
        lambda x: isinstance(x, (int, float))
    )].copy()
    if rows.empty:
        return
    rows["val_f1"]  = rows["val_f1"].astype(float)
    rows["val_acc"] = rows["val_acc"].astype(float)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, col, title in zip(
        axes,
        ["val_f1", "val_acc"],
        ["Val F1 (weighted)", "Val Accuracy"],
    ):
        for i, (tgt_g, grp) in enumerate(rows.groupby("target")):
            xs  = np.arange(len(grp)) + i * 0.36
            clr = [P["pri"], P["sec"]][i % 2]
            ax.bar(xs, grp[col], width=0.33, label=tgt_g,
                   color=clr, alpha=0.85)
            for xi, yi, m in zip(xs, grp[col], grp["model"]):
                ax.text(xi, yi + 0.005, m[:8], ha="center",
                        fontsize=6.5, color=P["txt"], rotation=30)
        ax.set_title(title, color=P["acc"], fontsize=12)
        ax.set_ylim(0, 1.1); ax.set_ylabel(title)
        ax.set_xticks([]); ax.legend(fontsize=9)

    fig.suptitle("Model Comparison — Channel & Tone Prediction",
                 fontsize=14, color=P["txt"])
    plt.tight_layout()
    plt.savefig("results/model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Model comparison   →  results/model_comparison.png")


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    from data_generator import generate_dataset
    df = generate_dataset(3000)
    df.to_csv("data/outreach_dataset.csv", index=False)
    train_and_evaluate(df)
