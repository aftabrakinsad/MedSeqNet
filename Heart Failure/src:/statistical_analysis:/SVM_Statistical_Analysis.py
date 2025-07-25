# -*- coding: utf-8 -*-
"""SVM_Statistical_Analysis.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1LVQAkn0tpUIYVjJ41ENv3dJKPN_pEiTX
"""

!pip install optuna

import optuna
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

X_train = pd.read_csv('/content/X_train_final.csv').values
y_train = pd.read_csv('/content/y_train_final.csv').values.astype(np.float32).flatten()

X_val = pd.read_csv('/content/X_val_processed.csv').values
y_val = pd.read_csv('/content/y_val_processed.csv').values.astype(np.float32).flatten()

X_combined_for_cv = np.concatenate((X_train, X_val), axis=0)
y_combined_for_cv = np.concatenate((y_train, y_val), axis=0)

def objective_svm(trial):
    C = trial.suggest_float('C', 1e-3, 1e2, log=True)
    kernel = trial.suggest_categorical('kernel', ['linear', 'rbf', 'poly', 'sigmoid'])

    params = {
        'C': C,
        'kernel': kernel,
        'probability': True,
        'random_state': 42
    }

    if kernel in ['rbf', 'poly', 'sigmoid']:
        params['gamma'] = trial.suggest_float('gamma', 1e-4, 1e1, log=True)

    if kernel == 'poly':
        params['degree'] = trial.suggest_int('degree', 2, 5)

    svm_model = SVC(**params)

    svm_model.fit(X_train, y_train)
    y_pred_proba_val = svm_model.predict_proba(X_val)[:, 1]

    if len(np.unique(y_val)) > 1:
        val_auc = roc_auc_score(y_val, y_pred_proba_val)
        val_loss = 1.0 - val_auc
    else:
        return float('inf')

    return val_loss

print("\n--- Starting Optuna Optimization Study for SVM Baseline (Minimizing 1-AUC) ---")
study_svm = optuna.create_study(direction='minimize', study_name='SVM_Optimization',
                              pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10))
study_svm.optimize(objective_svm, n_trials=200, show_progress_bar=True)

print("\n--- SVM Optimization Finished ---")
print(f"Number of finished trials: {len(study_svm.trials)}")
print(f"Best trial value (Validation 1-AUC): {study_svm.best_trial.value:.4f}")
print(f"Corresponding Best Validation AUC: {1 - study_svm.best_trial.value:.4f}")
print("Best SVM hyperparameters:")
best_params_svm = study_svm.best_trial.params
for key, value in best_params_svm.items():
    print(f"  {key}: {value}")

n_splits = 10
kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

svm_accuracy_scores = []
svm_auc_scores = []
svm_precision_scores = []
svm_recall_scores = []
svm_f1_scores = []

print(f"\n--- Starting {n_splits}-Fold Cross-Validation for Optimized SVM Baseline ---")

for fold, (train_index, val_index) in enumerate(kf.split(X_combined_for_cv, y_combined_for_cv)):
    print(f"\n--- Fold {fold+1}/{n_splits} ---")
    X_train_fold, X_val_fold = X_combined_for_cv[train_index], X_combined_for_cv[val_index]
    y_train_fold, y_val_fold = y_combined_for_cv[train_index], y_combined_for_cv[val_index]

    single_class_in_val_fold = (len(np.unique(y_val_fold)) <= 1)
    if single_class_in_val_fold:
        print(f"WARNING: Fold {fold+1} validation set contains only one class. AUC will be NaN.")

    svm_params_cv = {
        'C': best_params_svm['C'],
        'kernel': best_params_svm['kernel'],
        'probability': True,
        'random_state': 42
    }

    if svm_params_cv['kernel'] in ['rbf', 'poly', 'sigmoid']:
        svm_params_cv['gamma'] = best_params_svm['gamma']

    if svm_params_cv['kernel'] == 'poly':
        svm_params_cv['degree'] = best_params_svm['degree']

    svm_model_cv = SVC(**svm_params_cv)

    svm_model_cv.fit(X_train_fold, y_train_fold)
    y_pred_proba_svm = svm_model_cv.predict_proba(X_val_fold)[:, 1]
    y_pred_class_svm = svm_model_cv.predict(X_val_fold)

    svm_accuracy_scores.append(accuracy_score(y_val_fold, y_pred_class_svm))
    if not single_class_in_val_fold:
        svm_auc_scores.append(roc_auc_score(y_val_fold, y_pred_proba_svm))
    else:
        svm_auc_scores.append(np.nan)
    svm_precision_scores.append(precision_score(y_val_fold, y_pred_class_svm, zero_division=0))
    svm_recall_scores.append(recall_score(y_val_fold, y_pred_class_svm, zero_division=0))
    svm_f1_scores.append(f1_score(y_val_fold, y_pred_class_svm, zero_division=0))

    print(f"  SVM Baseline Fold {fold+1} Metrics:")
    print(f"    Accuracy: {svm_accuracy_scores[-1]:.4f}")
    print(f"    AUC: {svm_auc_scores[-1]:.4f}" if not np.isnan(svm_auc_scores[-1]) else "AUC: N/A")
    print(f"    Precision: {svm_precision_scores[-1]:.4f}")
    print(f"    Recall: {svm_recall_scores[-1]:.4f}")
    print(f"    F1-Score: {svm_f1_scores[-1]:.4f}")

print("\n" + "="*60)
print("--- Optimized SVM Baseline: 10-Fold Cross-Validation Results (Mean ± Standard Deviation) ---")
print(f"Accuracy: {np.nanmean(svm_accuracy_scores):.4f} ± {np.nanstd(svm_accuracy_scores):.4f}")
print(f"AUC: {np.nanmean(svm_auc_scores):.4f} ± {np.nanstd(svm_auc_scores):.4f}")
print(f"Precision: {np.nanmean(svm_precision_scores):.4f} ± {np.nanstd(svm_precision_scores):.4f}")
print(f"Recall: {np.nanmean(svm_recall_scores):.4f} ± {np.nanstd(svm_recall_scores):.4f}")
print(f"F1-Score: {np.nanmean(svm_f1_scores):.4f} ± {np.nanstd(svm_f1_scores):.4f}")

def bootstrap_confidence_interval(data, alpha=0.95, n_bootstraps=10000):
    if len(data) == 0 or np.all(np.isnan(data)):
        return (np.nan, np.nan)

    data = np.array(data)[~np.isnan(data)]
    if len(data) == 0:
        return (np.nan, np.nan)

    bootstrap_means = []
    for _ in range(n_bootstraps):
        sample = np.random.choice(data, size=len(data), replace=True)
        bootstrap_means.append(np.mean(sample))

    lower_percentile = (1 - alpha) / 2 * 100
    upper_percentile = (1 + alpha) / 2 * 100

    lower_bound = np.percentile(bootstrap_means, lower_percentile)
    upper_bound = np.percentile(bootstrap_means, upper_percentile)

    return (lower_bound, upper_bound)

print("\n--- Optimized SVM Baseline: 95% Confidence Intervals (from 10-Fold CV) ---")
ci_svm_accuracy = bootstrap_confidence_interval(svm_accuracy_scores)
ci_svm_auc = bootstrap_confidence_interval(svm_auc_scores)
ci_svm_precision = bootstrap_confidence_interval(svm_precision_scores)
ci_svm_recall = bootstrap_confidence_interval(svm_recall_scores)
ci_svm_f1 = bootstrap_confidence_interval(svm_f1_scores)

print(f"Accuracy CI: ({ci_svm_accuracy[0]:.4f}, {ci_svm_accuracy[1]:.4f})")
print(f"AUC CI: ({ci_svm_auc[0]:.4f}, {ci_svm_auc[1]:.4f})")
print(f"Precision CI: ({ci_svm_precision[0]:.4f}, {ci_svm_precision[1]:.4f})")
print(f"Recall CI: ({ci_svm_recall[0]:.4f}, {ci_svm_recall[1]:.4f})")
print(f"F1-Score CI: ({ci_svm_f1[0]:.4f}, {ci_svm_f1[1]:.4f})")