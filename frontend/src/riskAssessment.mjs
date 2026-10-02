// Policy choices for an assumption-only assessment, not fitted coefficients.
export function assessRisk(values,approvalScale=90){
 const keys=['compensation','documentation','disputes','approval_days'];
 if(!Number.isFinite(approvalScale)||approvalScale<=0||approvalScale>3650)return null;
 if(keys.some(k=>values[k]===''||values[k]==null||!Number.isFinite(Number(values[k]))))return null;
 const v=Object.fromEntries(keys.map(k=>[k,Number(values[k])]));
 if(keys.some(k=>v[k]<0)||['compensation','documentation','disputes'].some(k=>v[k]>100)||v.approval_days>3650)return null;
 const components=[['Unpaid compensation',100-v.compensation],['Incomplete documentation',100-v.documentation],['Parcels with unresolved disputes',v.disputes],['Assumed approval wait',Math.min(100,100*v.approval_days/approvalScale)]];
 const score=components.reduce((sum,[,value])=>sum+value/4,0);
 return {score,band:score<33?'Low':score<67?'Medium':'High',components:components.map(([label,value])=>({label,value,contribution:value/4}))};
}
