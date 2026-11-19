"""Reproduce the small ridge model locally. Requires numpy and openpyxl."""
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
import numpy as np
from core import ROOT, FEATURE_NAMES, codes, features, norm, schedule_rows, workbook_rows


def main():
    rng = random.Random(42)
    courses = []
    snapshots = []
    for path in sorted((ROOT / 'data/raw').glob('*.xlsx')):
        blob = path.read_bytes()
        rows, _ = workbook_rows(blob, path.stem)
        courses.extend(rows)
        snapshots.append({'file': path.name, 'sha256': hashlib.sha256(blob).hexdigest(), 'records': len(rows)})
    if not courses:
        raise SystemExit('Put the four exported experimental workbooks in data/raw first.')
    schedule = schedule_rows((ROOT / 'data/raw/WN2027.csv').read_bytes(), 'Winter 2027')
    unique = {}
    for row in schedule:
        unique.setdefault((tuple(codes(row['code'])), norm(row['title'])), row)
    schedule = list(unique.values())
    by_code, by_subject = defaultdict(list), defaultdict(list)
    for row in schedule:
        for code in codes(row['code']):
            by_code[code].append(row)
            by_subject[code[0]].append(row)
    pairs = []
    dedup = set()
    for row in courses:
        key = tuple(codes(row['code']))
        if not key or (key, norm(row['title'])) in dedup:
            continue
        dedup.add((key, norm(row['title'])))
        positives = [s for code in key for s in by_code[code]]
        for s in positives[:2]:
            pairs.append((key, row, s, 1))
        if not positives:
            continue
        negatives = [s for s in by_subject[key[0][0]] if not set(codes(s['code'])) & set(key) and norm(s['title']) != norm(row['title'])]
        negatives.sort(key=lambda s: features(row, s)[0], reverse=True)
        for s in negatives[:2]:
            pairs.append((key, row, s, 0))
        if len(negatives) > 2:
            pairs.append((key, row, rng.choice(negatives[2:]), 0))
    groups = sorted(set(k for k, *_ in pairs))
    rng.shuffle(groups)
    n = len(groups)
    train_keys, val_keys, test_keys = set(groups[:int(n*.6)]), set(groups[int(n*.6):int(n*.8)]), set(groups[int(n*.8):])
    assert train_keys.isdisjoint(val_keys | test_keys) and val_keys.isdisjoint(test_keys)
    def data(keys):
        records = [p for p in pairs if p[0] in keys]
        return np.array([[1] + features(a, b) for _, a, b, _ in records]), np.array([y for *_, y in records], dtype=float)
    X, y = data(train_keys)
    V, vy = data(val_keys)
    T, ty = data(test_keys)
    if min(len(y), len(vy), len(ty)) < 10:
        raise SystemExit('Not enough independent matched course groups to train and evaluate.')
    def fit(x, target, alpha):
        penalty = np.eye(x.shape[1]) * alpha
        penalty[0, 0] = 0
        return np.linalg.solve(x.T @ x + penalty, x.T @ target)
    tuning = []
    for alpha in [.1, 1, 10, 100]:
        coef = fit(X, y, alpha)
        tuning.append((float(np.mean((V @ coef - vy)**2)), alpha))
    mse, alpha = min(tuning)
    w = fit(X, y, alpha)
    pred = T @ w
    labels = pred >= .55
    tp = int(np.sum(labels & (ty == 1)))
    fp = int(np.sum(labels & (ty == 0)))
    fn = int(np.sum(~labels & (ty == 1)))
    evaluation = {'test_pairs': len(ty), 'test_course_groups': len(test_keys), 'rmse': float(np.sqrt(np.mean((pred-ty)**2))),
                  'precision_at_055': tp/max(1,tp+fp), 'recall_at_055': tp/max(1,tp+fn),
                  'true_positives': tp, 'false_positives': fp, 'false_negatives': fn,
                  'title_similarity_baseline_rmse': float(np.sqrt(np.mean((T[:,1]-ty)**2))),
                  'validation_mse': mse, 'alpha': alpha,
                  'limitation': 'Weak labels from exact course identifiers, not human-adjudicated identity or renumbering labels. Metrics do not establish real-world renumbering accuracy. Split by source course identifier; target-catalog rows may recur as negative candidates.'}
    # Evaluate before refitting. The shipped model uses train+validation, never the held-out test groups.
    final = fit(np.concatenate([X,V]), np.concatenate([y,vy]), alpha)
    model = {'version':'ridge-2026-11-19-v1', 'method':'Ridge linear regression', 'feature_names':FEATURE_NAMES,
             'intercept':float(final[0]), 'coefficients':final[1:].tolist(), 'review_threshold':.55,
             'training_records':len(y)+len(vy), 'source_course_rows':len(courses), 'label_source':'Weak identity labels from real experimental workbook identifiers joined to Winter 2027 Registrar schedule; distinct identifiers within subject are negative candidates. No synthetic performance claims.',
             'evaluation':evaluation, 'seed':42, 'snapshots':snapshots,
             'schedule_sha256':hashlib.sha256((ROOT/'data/raw/WN2027.csv').read_bytes()).hexdigest(),
             'split':{'train_course_groups':len(train_keys),'validation_course_groups':len(val_keys),'test_course_groups':len(test_keys)}}
    (ROOT/'models').mkdir(exist_ok=True)
    (ROOT/'models/ridge.json').write_text(json.dumps(model,indent=2))
    (ROOT/'reports/model_evaluation.json').write_text(json.dumps(model,indent=2))
    print(json.dumps({'course_rows':len(courses),'unique_schedule_courses':len(schedule),'pairs':len(pairs),'evaluation':evaluation},indent=2))


if __name__ == '__main__':
    main()
