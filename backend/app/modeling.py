"""Request-local temporal evaluation with explicit provenance attestations."""
from datetime import date
import numpy as np
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,precision_score,recall_score,f1_score,confusion_matrix
from sklearn.calibration import calibration_curve
from .analysis import parse,validate_settings,mapped,date_list,number,FACTORS

FEATURES=['required_hectares_at_snapshot','acquisition_progress_pct_at_snapshot','days_to_original_plan_at_snapshot','source_age_days_at_snapshot']
def metrics(y,p):
    pred=p>=.5
    return {'roc_auc':float(roc_auc_score(y,p)),'pr_auc':float(average_precision_score(y,p)),
            'brier':float(brier_score_loss(y,p)),'precision':float(precision_score(y,pred,zero_division=0)),
            'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),
            'confusion_matrix':confusion_matrix(y,pred).tolist()}
def train(req):
    s=req.settings; headers,rows=parse(req.csv_text);validate_settings(headers,s)
    # Attestations cannot be inferred from names such as "delay" or from a date column alone.
    if not all([req.verified_outcomes,req.verified_snapshot_inputs,req.verified_plan_at_snapshot,req.verification_note.strip()]):
        raise ValueError('Verify outcomes, input availability, and the original plan at the snapshot; provide a source/verification explanation.')
    required=['project_id','land_required','land_acquired','observation_date','source_date','source_reference','planned_completion','actual_completion']
    if any(k not in s.mapping for k in required): raise ValueError('Modeling requires mapped project ID, land fields, observation/source dates, source reference, and planned/actual completion dates.')
    if len(rows)<100: raise ValueError('At least 100 complete, distinct historical projects are required for this evaluation. This minimum is an engineering guard, not proof of statistical sufficiency.')
    ids=set(); prepared=[]
    for i,r in enumerate(rows):
        v=mapped(r,s);id=v['project_id']
        if not id or id in ids: raise ValueError('Each historical project must have one distinct, nonblank identifier. Resolve repeats before modeling.')
        ids.add(id)
        if not v['source_reference']: raise ValueError(f'Row {i+1}: source reference required.')
        dates={k:date_list(v.get(k,''),s.date_format) for k in ['observation_date','source_date','planned_completion','actual_completion']}
        if any(not d or len(d)!=1 for d in dates.values()): raise ValueError(f'Row {i+1}: one valid date required for each modeling date field.')
        obs,source,planned,actual=[dates[k][0] for k in dates]
        if actual>date.today(): raise ValueError(f'Row {i+1}: an actual completion outcome cannot be in the future.')
        # Outcomes must occur after prediction time. Published inputs must already be available.
        if source>obs or planned<=obs or actual<=obs: raise ValueError(f'Row {i+1}: require source date ≤ snapshot < planned and actual completion dates.')
        a,b=number(v['land_required']),number(v['land_acquired'])
        if a is None or b is None or a<=0 or b>a: raise ValueError(f'Row {i+1}: valid land inputs at the snapshot required.')
        x=[a*FACTORS[s.area_unit],100*b/a,(planned-obs).days,(obs-source).days]
        if not all(np.isfinite(x)): raise ValueError('Model input range exceeded.')
        prepared.append((obs,i,id,x,int(actual>planned),actual))
    prepared.sort(key=lambda r:r[0]); dates=sorted(set(r[0] for r in prepared))
    if len(dates)<10: raise ValueError('At least 10 distinct snapshot dates required for temporal evaluation.')
    # Keep equal snapshot dates together; no project or same-date boundary crosses partitions.
    cut1=dates[int(len(dates)*.4)];cut2=dates[int(len(dates)*.6)];cut3=dates[int(len(dates)*.8)]
    parts=[[r for r in prepared if r[0]<cut1],[r for r in prepared if cut1<=r[0]<cut2],[r for r in prepared if cut2<=r[0]<cut3],[r for r in prepared if r[0]>=cut3]]
    if any(len(p)<15 or min(sum(r[4]==0 for r in p),sum(r[4]==1 for r in p))<5 for p in parts): raise ValueError('Each of four temporal partitions needs at least 15 projects and five examples of each outcome; add more verified history.')
    for earlier,later in zip(parts,parts[1:]):
        if max(r[5] for r in earlier)>=min(r[0] for r in later):
            raise ValueError('Earlier-partition outcomes must be observed before the next partition begins. Use separated historical cohorts to prevent future-outcome leakage.')
    arrays=[(np.array([r[3] for r in p]),np.array([r[4] for r in p])) for p in parts]
    (xt,yt),(xv,yv),(xc,yc),(xe,ye)=arrays
    models={'Logistic regression':make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',random_state=2026,max_iter=1000)),
            'Random forest':RandomForestClassifier(n_estimators=150,max_depth=5,min_samples_leaf=5,class_weight='balanced',random_state=2026,n_jobs=1),
            'Gradient boosting':GradientBoostingClassifier(n_estimators=100,max_depth=2,min_samples_leaf=5,learning_rate=.05,random_state=2026),
            'XGBoost':XGBClassifier(n_estimators=150,max_depth=3,learning_rate=.05,min_child_weight=5,subsample=1.0,colsample_bytree=1.0,reg_lambda=2.0,objective='binary:logistic',eval_metric='logloss',tree_method='hist',random_state=2026,n_jobs=1)}
    results={}; fitted={}
    def logit(p):
        p=np.clip(p,1e-6,1-1e-6);return np.log(p/(1-p)).reshape(-1,1)
    for name,m in models.items():
        if name in ('Gradient boosting','XGBoost'): m.fit(xt,yt,sample_weight=compute_sample_weight('balanced',yt))
        else: m.fit(xt,yt)
        # Select before calibration. Neither calibration nor test outcomes choose the model.
        results[name]=metrics(yv,m.predict_proba(xv)[:,1]);fitted[name]=m
    selected=min(results,key=lambda k:(results[k]['brier'],-results[k]['pr_auc']))
    m=fitted[selected]
    cal=LogisticRegression(C=1,random_state=2026).fit(logit(m.predict_proba(xc)[:,1]),yc)
    calibrated=lambda x:cal.predict_proba(logit(m.predict_proba(x)[:,1]))[:,1]
    pe=calibrated(xe)
    baseline=np.repeat(float(yt.mean()),len(ye));test=metrics(ye,pe);base=metrics(ye,baseline)
    active=test['brier']<base['brier'] and test['roc_auc']>.5
    frac,mean=calibration_curve(ye,pe,n_bins=5,strategy='quantile')
    # Permutation changes one held-out feature at a time; importance is association only.
    rng=np.random.default_rng(2026);importance=[]
    for j in range(len(FEATURES)):
        changes=[]
        for repeat in range(10):
            altered=xe.copy();altered[:,j]=rng.permutation(altered[:,j])
            changes.append(float(brier_score_loss(ye,calibrated(altered)))-test['brier'])
        importance.append(float(np.mean(changes)))
    method='Held-out permutation importance: increase in Brier error after shuffling each feature (10 repeats). Negative values are retained. Not a causal effect.'
    boot=[]
    for repeat in range(300):
        indices=rng.integers(0,len(ye),len(ye));boot.append(float(brier_score_loss(ye[indices],pe[indices])))
    interval=[float(v) for v in np.quantile(boot,[.025,.975])]
    median=np.median(xt,axis=0);local=[];reference_probabilities=[]
    for j in range(len(FEATURES)):
        changed=xe.copy();changed[:,j]=median[j];reference_probabilities.append(calibrated(changed))
    for i in range(len(xe)):
        effects=[]
        for j,key in enumerate(FEATURES):
            effects.append({'feature':key,'uploaded_value':float(xe[i,j]),'training_reference':float(median[j]),'probability_difference':float(pe[i]-reference_probabilities[j][i])})
        local.append(sorted(effects,key=lambda e:-abs(e['probability_difference'])))
    return {'status':'evaluated','prediction_enabled':active,'selected_model':selected,'target':'Actual completion later than the plan recorded at the input snapshot. Binary outcome only; no duration forecast.',
            'model_version':'2.1.0','features':FEATURES,'uncertainty':{'brier_95_percent_bootstrap_interval':interval,'resamples':300,'note':'Sampling variability of aggregate test error conditional on this fitted model; not an individual prediction interval.'},'split':{'method':'Chronological 40% train / 20% select / 20% calibrate / 20% test of distinct snapshot dates','counts':[len(p) for p in parts],'date_ranges':[[str(p[0][0]),str(p[-1][0])] for p in parts],'class_counts':[{'on_time':int((y==0).sum()),'late':int((y==1).sum())} for x,y in arrays]},
            'validation_candidates':results,'test_metrics':test,'test_baseline':base,'calibration':{'method':'Logistic probability recalibration on an independent calibration partition','mean_probability':mean.tolist(),'observed_fraction':frac.tolist()},
            'global_explanation':{'method':method,'values':dict(zip(FEATURES,importance))},
            'heldout_predictions':[{'row_index':r[1],'project_id':r[2],'probability':float(p),'observed_outcome':r[4],'local_sensitivity':local[i]} for i,(r,p) in enumerate(zip(parts[3],pe))] if active else [],
            'verification_note':req.verification_note,'limitations':['Verification is user-attested, not independently established by the application.','Training, selection, calibration and test use four disjoint chronological cohorts; engineering cutoffs are not a statistical sufficiency guarantee.','Four snapshot-supported features are used; selection bias, changing plans and external validity remain untested.','Predictions shown are held-out evaluation results only. No new-project forecast endpoint or saved model is provided.','Passing the baseline gate does not establish deployment readiness.','Local sensitivity replaces one feature with its training median. Differences need not sum to the probability and may represent infeasible combinations; they are not intervention effects.','All training is request-local and the fitted estimators are discarded after evaluation.'],
            'reason':'Held-out evaluation probabilities available.' if active else 'No held-out predictions displayed: selected model did not beat the prevalence baseline in Brier score with ROC-AUC above 0.5.'}
