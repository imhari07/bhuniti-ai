# BhuNiti AI · Judge walkthrough

## 90-second explanation

“We are Team Nexora. BhuNiti AI turns an officer’s uploaded CSV into traceable land-acquisition intelligence.

First, we confirm column meanings, units and date formats. We preserve missing values rather than inventing evidence.

This evidence briefing shows which fields are present. The review queue brings records with more evidence flags to the officer’s attention; it does not call those projects delayed.

Open a project: each indicator shows its formula and uploaded operands. Required land of 200 hectares and acquired land of 1.68958 hectares produce approximately 0.845% progress.

A what-if change to acquired land recalculates arithmetic on a temporary copy. It neither alters the source nor proves a delay reduction.

Our predictive pipeline is available only for sufficient verified historical data. It compares four algorithms, using separate time groups to train, select, calibrate and test. That separation helps prevent later information from influencing earlier decisions.

The six records currently uploaded lack verified completion outcomes, so we do not display predictive accuracy or delay probabilities for them.

An officer reviews the evidence, adds notes and downloads the findings. The application does not persist uploaded records.”

## How the upgraded predictive pipeline works

1. Verify original plans, actual completion outcomes and input availability at each historical snapshot. User attestations are not independent verification.
2. Derive four inputs known at that snapshot: required hectares, acquired percentage, days to the original plan, and source age. Actual completion is used only to construct the outcome.
3. Split distinct snapshot dates into 40% training, 20% model selection, 20% probability calibration, and 20% testing. Require outcomes from each earlier group to be known before the next group begins.
4. Fit XGBoost, Logistic Regression, Random Forest and Gradient Boosting on training records, accounting for class imbalance.
5. Choose using selection-set Brier error, with PR-AUC as a tie-breaker. Calibrate only the chosen model on the separate calibration set.
6. Evaluate the latest test set against a prevalence baseline. Show precision, recall, F1, ROC-AUC, PR-AUC, Brier, class balance, calibration bins and confusion matrix. Display historical test probabilities only if the model passes the baseline gate.
7. Explain sensitivity: global feature shuffling measures how much error increases; local comparisons replace one feature with its training median. Neither is a causal explanation.
8. Show a bootstrap interval for overall test error. It is not a confidence band for a particular project.

## Honest answers

**What improved?** Validation separation, an additional candidate algorithm, two additional snapshot-supported features, calibration, uncertainty reporting, explanation and review presentation.

**Did prediction accuracy improve?** We cannot establish that without eligible real historical records. We improved the evaluation pipeline and tested its mechanics.

**What can you show today?** A working upload-to-review workflow on real source records, explicit evidence checks, traceable calculations and arithmetic comparisons.

**What does the system need next?** An authorized historical dataset with original plans, actual outcomes and verified inputs available at each snapshot, followed by an officer pilot and external evaluation.


XGBoost is installed and actively fitted in every eligible historical evaluation. CPU histogram trees, fixed seed 2026 and balanced training weights are used. It competes on the same selection partition; the winning model alone is calibrated on the separate calibration partition. XGBoost is not guaranteed to win, and the six-record upload remains descriptive-only.
