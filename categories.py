"""Multilabel ridge regression over course text. Inference needs no API or NumPy."""
import json
import math
import re
from collections import Counter, defaultdict
from core import ROOT, STOP, codes, norm

FIELDS={'Subject':'tags','Functional Area':'functional_area','Sustainability Subtags':'sustainability_subtags'}


def terms(row):
    words=[w for w in norm(str(row.get('title',''))+' '+str(row.get('description',''))).split() if w not in STOP and len(w)>2]
    return words+[' '.join(words[i:i+2]) for i in range(len(words)-1)]+['dept_'+c[0].lower() for c in codes(row.get('code',''))]


def vector(row, model):
    counts=Counter(terms(row)); entries=[]
    for token,count in counts.items():
        i=model['vocabulary'].get(token)
        if i is not None: entries.append((i,(1+math.log(count))*model['idf'][i]))
    length=math.sqrt(sum(v*v for _,v in entries)) or 1
    return [(i,v/length) for i,v in entries]


def predict(row, model):
    x=vector(row,model); result={}
    for field,m in model['fields'].items():
        ranked=sorted(((label,max(0,min(1,m['intercepts'][j]+sum(v*m['weights'][i][j] for i,v in x)))) for j,label in enumerate(m['labels'])),key=lambda p:p[1],reverse=True)
        selected=[label for label,s in ranked if s>=m['threshold']] if x else []
        tentative=False
        if x and not selected and ranked:
            selected=[ranked[0][0]];tentative=True
        result[field]={'labels':selected,'scores':{l:round(s,3) for l,s in ranked[:5]},'tentative':tentative,'review_required':True}
    return {'code':str(row.get('code',''))[:100],'title':str(row.get('title',''))[:1000],
            'categories':result,'text_coverage':bool(x),'decision':'Pending','model_version':model['version']}


def attach(result,model):
    for r in result.get('suggestions',[])+result.get('discovery',[]):
        p=predict(r,model)
        for field,details in p['categories'].items():r['suggested_'+field.lower().replace(' ','_')]=', '.join(details['labels'])
    result['category_model']={k:model[k] for k in ['version','method','training_courses','evaluation']}
    return result


def train():
    import random
    import numpy as np
    from core import workbook_rows
    records={}
    for p in sorted((ROOT/'data/raw').glob('*.xlsx')):
        rows,_=workbook_rows(p.read_bytes(),p.stem)
        for r in rows:
            if r['not_current'] or not r['title'] or not codes(r['code']):continue
            key=(tuple(codes(r['code'])),norm(r['title']))
            if key not in records:records[key]={**r,'labels':{f:set() for f in FIELDS}}
            for field,column in FIELDS.items():records[key]['labels'][field].update(x.strip() for x in r.get(column,'').split(',') if x.strip())
    rows=list(records.values());groups=sorted({tuple(codes(r['code'])) for r in rows});random.Random(42).shuffle(groups)
    n=len(groups);train_groups=set(groups[:int(n*.7)]);val_groups=set(groups[int(n*.7):int(n*.85)]);test_groups=set(groups[int(n*.85):])
    assert train_groups.isdisjoint(val_groups|test_groups) and val_groups.isdisjoint(test_groups)
    train_rows=[r for r in rows if tuple(codes(r['code'])) in train_groups]
    df=Counter(t for r in train_rows for t in set(terms(r)))
    vocab=[t for t,c in df.most_common(650) if c>=2]
    model={'version':'category-ridge-2026-11-19-v1','method':'TF-IDF text features + multilabel ridge linear regression','vocabulary':{t:i for i,t in enumerate(vocab)},'idf':[math.log((1+len(train_rows))/(1+df[t]))+1 for t in vocab], 'fields':{},'training_courses':len(rows),'evaluation':{}}
    def matrix(rs):
        x=np.zeros((len(rs),len(vocab)+1));x[:,-1]=1
        for i,r in enumerate(rs):
            for j,v in vector(r,model):x[i,j]=v
        return x
    train_ids=[i for i,r in enumerate(rows) if tuple(codes(r['code'])) in train_groups]
    val_ids=[i for i,r in enumerate(rows) if tuple(codes(r['code'])) in val_groups]
    test_ids=[i for i,r in enumerate(rows) if tuple(codes(r['code'])) in test_groups]
    X=matrix(rows);penalty=np.eye(X.shape[1])*2;penalty[-1,-1]=0
    def metrics(y,p):
        tp=int(((y==1)&p).sum());fp=int(((y==0)&p).sum());fn=int(((y==1)&~p).sum())
        return {'micro_precision':tp/max(1,tp+fp),'micro_recall':tp/max(1,tp+fn),'micro_f1':2*tp/max(1,2*tp+fp+fn)}
    for field in FIELDS:
        # Missing cells are unlabeled, not negative examples.
        available=[i for i in range(len(rows)) if rows[i]['labels'][field]]
        tr=[i for i in train_ids if i in available];va=[i for i in val_ids if i in available];te=[i for i in test_ids if i in available]
        labels=sorted({l for i in tr for l in rows[i]['labels'][field]})
        y=np.array([[float(l in r['labels'][field]) for l in labels] for r in rows])
        coef=np.linalg.solve(X[tr].T@X[tr]+penalty,X[tr].T@y[tr])
        threshold=max([.15,.25,.35,.45],key=lambda t:metrics(y[va],(X[va]@coef)>=t)['micro_f1']) if va else .35
        evaluation={**metrics(y[te],(X[te]@coef)>=threshold),'held_out_courses':len(te),'training_labeled_courses':len(tr),'labels':len(labels),'threshold':threshold,'note':'Grouped by course identifier. Title/department only; scores are not calibrated probabilities. Sparse and absent labels require human review.'}
        model['evaluation'][field]=evaluation
        fit_ids=tr+va;final=np.linalg.solve(X[fit_ids].T@X[fit_ids]+penalty,X[fit_ids].T@y[fit_ids])
        model['fields'][field]={'labels':labels,'weights':final[:-1].tolist(),'intercepts':final[-1].tolist(),'threshold':threshold}
    (ROOT/'models/categories.json').write_text(json.dumps(model,separators=(',',':')))
    (ROOT/'reports/category_evaluation.json').write_text(json.dumps({'version':model['version'],'training_courses':len(rows),'evaluation':model['evaluation']},indent=2))
    print(json.dumps({'training_courses':len(rows),'evaluation':model['evaluation']},indent=2))


if __name__=='__main__':train()
