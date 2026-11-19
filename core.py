"""Local course reconciliation. No network requests or model-service dependency."""
import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
SCHEDULE_URL = 'https://ro.umich.edu/calendars/schedule-classes'
STOP = {'the', 'and', 'of', 'in', 'to', 'for', 'a', 'an', 'with', 'on', 'at', 'introduction'}
FEATURE_NAMES = ['title_sequence', 'title_jaccard', 'title_containment', 'same_subject', 'title_length_ratio', 'same_level']
IMPACT = re.compile(r'climate|sustainab|environmental justice|social (?:impact|justice|change|innovation)|poverty|human rights|inequal|renewable|microfinance|nonprofit|public policy|food systems|community develop|clean energy|conservation|decarbon|health equity', re.I)


def norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower()).strip()


def tokens(value):
    return set(norm(value).split()) - STOP


def codes(value):
    text = str(value or '').upper().replace('&', ' ')
    return list(dict.fromkeys((re.sub(r'\s+', '', s), n) for s, n in re.findall(r'([A-Z][A-Z /-]*?)\s+(\d{3,4}[A-Z]?)\b', text)))


def features(a, b):
    at, bt = tokens(a['title']), tokens(b['title'])
    ac, bc = codes(a.get('code')), codes(b.get('code'))
    overlap = len(at & bt)
    return [SequenceMatcher(None, norm(a['title']), norm(b['title'])).ratio(),
            overlap / max(1, len(at | bt)), overlap / max(1, min(len(at), len(bt))),
            float(any(x[0] == y[0] for x in ac for y in bc)),
            min(len(norm(a['title'])), len(norm(b['title']))) / max(1, len(norm(a['title'])), len(norm(b['title']))),
            float(any(x[1][0] == y[1][0] for x in ac for y in bc))]


def score(a, b, model):
    return max(0.0, min(1.0, model['intercept'] + sum(x * w for x, w in zip(features(a, b), model['coefficients']))))


def safe_workbook(blob):
    if len(blob) > 10_000_000:
        raise ValueError('Each workbook must be under 10 MB.')
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            if sum(x.file_size for x in z.infolist()) > 45_000_000 or len(z.infolist()) > 1500:
                raise ValueError('Workbook expands beyond the safe processing limit.')
        return load_workbook(io.BytesIO(blob), read_only=True, data_only=False, keep_links=False)
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError('Upload an Excel .xlsx workbook, not a Google Sheets shortcut or .xls file.') from e


def workbook_rows(blob, dataset):
    book = safe_workbook(blob)
    rows, warnings = [], []
    found = set()
    try:
        for sheet in book:
            kind = norm(sheet.title)
            if kind not in {'courses', 'not current'}:
                continue
            found.add(kind)
            if (sheet.max_row or 0) > 12000 or (sheet.max_column or 0) > 100:
                raise ValueError('Course sheets must have fewer than 12,000 rows and 100 columns.')
            values = sheet.iter_rows(values_only=True)
            headers = [norm(x) for x in next(values, ())]
            def col(names, fallback=None):
                return next((i for i, h in enumerate(headers) if h in names), fallback)
            ti, ci = col({'course name', 'title'}), col({'course no', 'course number', 'course code'})
            if ti is None or ci is None:
                raise ValueError(f'{dataset} / {sheet.title}: expected Course Name and Course No. or Course Number headers.')
            termi = col({'term offered'})
            li = col({'course link'}, 5 if kind == 'not current' else None)
            subj = col({'subject', 'course subject', 'social causes'})
            school = col({'affiliated school'})
            for n, cells in enumerate(values, 2):
                if n > 12000 or len(cells) > 100:
                    raise ValueError('Course sheet exceeds the safe row/column limits.')
                get = lambda i: str(cells[i] or '').strip() if i is not None and i < len(cells) else ''
                title, code = get(ti), get(ci)
                if not title and not code:
                    continue
                if not title or not code:
                    warnings.append(f'{dataset} / {sheet.title} row {n}: incomplete title or identifier; retained for review.')
                link = get(li)
                if link.startswith('='):
                    link = ''
                rows.append({'dataset': dataset, 'sheet': sheet.title, 'row': n, 'title': title,
                             'code': code, 'term': get(termi), 'link': link, 'tags': get(subj),
                             'school': get(school), 'not_current': kind == 'not current'})
    finally:
        book.close()
    if 'courses' not in found or 'not current' not in found:
        raise ValueError(f'{dataset}: both Courses and Not Current tabs are required (capitalization may differ).')
    if not rows:
        raise ValueError(f'{dataset}: no course records found.')
    return rows, warnings


def schedule_rows(blob, term):
    """Accept Registrar CSV and a minimal documented normalized CSV."""
    if len(blob) > 15_000_000:
        raise ValueError('Schedule CSV must be under 15 MB.')
    text = blob.decode('utf-8-sig', errors='strict')
    if '<html' in text[:1000].lower() or '<!doctype' in text[:1000].lower():
        raise ValueError('The schedule file is a login page. Download the CSV after signing in to U-M.')
    sample = text[:8000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',\t;')
    except csv.Error:
        dialect = csv.excel
    table = list(csv.reader(io.StringIO(text), dialect))
    if len(table) > 150001:
        raise ValueError('Schedule has too many rows.')
    header_at = next((i for i, r in enumerate(table[:15]) if any(norm(c) in {'subject', 'subject code', 'subject abbrev', 'course code', 'course no', 'course number'} for c in r)), None)
    if header_at is None:
        raise ValueError('Schedule headers not recognized. Use the normalized template: subject, catalog_number, title, section, term, url.')
    headers = [norm(x) for x in table[header_at]]
    def col(names):
        return next((i for i, h in enumerate(headers) if h in names), None)
    si = col({'subject', 'subject code', 'subject abbrev', 'subject abbreviation'})
    ni = col({'catalog', 'catalog number', 'catalog nbr', 'catalog num', 'cat nbr', 'course number', 'course nbr', 'course no'})
    ci = col({'course code'})
    ti = col({'title', 'course title', 'course name', 'descr', 'description', 'class title'})
    seci = col({'section', 'section number', 'class section', 'class sect', 'sect'})
    li = col({'url', 'course link', 'link'})
    tri = col({'term', 'term offered'})
    if ti is None or (ci is None and (si is None or ni is None)):
        raise ValueError('Schedule needs subject + catalog_number (or course_code), and title. Rename columns using the CSV template.')
    unique = {}
    for row in table[header_at + 1:]:
        get = lambda i: str(row[i] or '').strip() if i is not None and i < len(row) else ''
        title = get(ti)
        subject = get(si)
        abbr = re.search(r'\(([A-Z &/-]+)\)\s*$', subject)
        subject = abbr[1] if abbr else subject
        code = get(ci) if ci is not None else f'{subject} {get(ni)}'
        parsed = codes(code)
        if not title or not parsed:
            continue
        actual_term = get(tri)
        if actual_term and norm(actual_term) not in {norm(term), norm(term.replace('20', '')), norm(term.replace('Winter', 'WN').replace('Fall', 'FA').replace(' ', ''))}:
            raise ValueError(f'Schedule term {actual_term!r} does not match selected {term}.')
        key = (tuple(parsed), norm(title), get(seci))
        unique[key] = {'code': code, 'title': title, 'section': get(seci), 'term': term, 'link': get(li) or SCHEDULE_URL}
    if not unique:
        raise ValueError('No valid schedule records found. Check the header names and course identifiers.')
    return list(unique.values())


def topic_specific(row):
    return bool(re.search(r'\(\s*\d{1,3}\s*\)', row.get('code', '')) or re.search(r'\btopics?\b|independent|directed (?:study|reading)', row['title'], re.I))


def add_term(old, target):
    short = target.replace('20', '')
    terms = [x.strip() for x in old.split(',') if x.strip() and 'not current' not in x.lower()]
    if not any(norm(x) in {norm(short), norm(target)} for x in terms):
        terms.append(short)
    return ', '.join(terms)


def reconcile(courses, schedule, term, model, history=None):
    history = history or {}
    by_code, inverted = defaultdict(list), defaultdict(set)
    for i, s in enumerate(schedule):
        for code in codes(s['code']):
            by_code[code].append(i)
        for token in tokens(s['title']):
            inverted[token].add(i)
    known = {c for r in courses for c in codes(r['code'])}
    suggestions = []
    for row in courses:
        ids = set(i for code in codes(row['code']) for i in by_code[code])
        matches = [schedule[i] for i in ids]
        exact = max(matches, key=lambda s: features(row, s)[0], default=None)
        out = {**row, 'action': 'Review missing offering', 'proposed_code': row['code'], 'proposed_term': row['term'],
               'proposed_link': row['link'], 'evidence': '', 'score': None, 'decision': 'Pending', 'notes': ''}
        if not codes(row['code']) or not row['title']:
            out.update(action='Review invalid record', evidence='Missing or unrecognized identifier/title.')
        elif any(part.strip() and norm(part) != 'not current' and not re.fullmatch(r'(?:Winter|Fall|Spring(?:/Summer)?|Summer)\s+\d{2}(?:\d{2})?(?:\s*\([AB]\))?', part.strip(), re.I) for part in row['term'].split(',')):
            out.update(action='Review invalid record', evidence='Term Offered contains unexpected text. Check column alignment in the source copy before proposing a term or tab change.')
        elif exact:
            sim = features(row, exact)[0]
            section = re.search(r'\(\s*(\d{1,3})\s*\)', row['code'])
            section_matches = not section or str(exact.get('section', '')).zfill(3) == section[1].zfill(3)
            specific = topic_specific(row)
            if sim < .50 or (specific and (sim < .90 or not section_matches)):
                out.update(action='Review topic / title', evidence=f'Identifier appears as “{exact["title"]}”; verify the specific topic/section. No automatic term update.', score=round(score(row, exact, model), 4))
            else:
                proposed = add_term(row['term'], term)
                action = 'Reactivate course' if row['not_current'] else ('Update term offered' if proposed != row['term'] else 'Already current')
                out.update(action=action, proposed_term=proposed, evidence=f'Exact identifier found in {term}: {exact["code"]} — {exact["title"]}. Verify A/B part-term and course link.', score=round(score(row, exact, model), 4))
                if not row['link']:
                    out['proposed_link'] = exact['link']
        else:
            pool = set(i for t in tokens(row['title']) for i in inverted[t])
            # shortcut: lexical shortlist is capped at 100; use a search index for much larger catalogs.
            ranked = sorted(pool, key=lambda i: len(tokens(row['title']) & tokens(schedule[i]['title'])), reverse=True)[:100]
            candidate = max((schedule[i] for i in ranked), key=lambda s: score(row, s, model), default=None)
            if candidate and features(row, candidate)[0] >= .65 and score(row, candidate, model) >= model.get('review_threshold', .55):
                out.update(action='Review possible renumbering', proposed_code=candidate['code'], score=round(score(row, candidate, model), 4), evidence=f'Possible identity match: {candidate["code"]} — {candidate["title"]}. A reviewer must confirm renumbering; title similarity alone is insufficient.')
            else:
                seen = [t for t, rs in history.items() if any(set(codes(row['code'])) & set(codes(s['code'])) for s in rs)]
                out['evidence'] = f'Not found in {term}. Missing one term does not mean discontinued. '
                out['evidence'] += ('Found in historical schedules: ' + ', '.join(seen) + '. Keep Fall/Winter courses available.' if seen else 'History is incomplete; verify the last actual offering before moving to Not Current (>1 year).')
                if row['not_current']:
                    out['action'] = 'Keep Not Current / review'
        suggestions.append(out)
    discovery = []
    seen_discovery = set()
    for s in schedule:
        if set(codes(s['code'])) & known or not IMPACT.search(s['title']):
            continue
        key = (s['code'], s['title'])
        if key in seen_discovery:
            continue
        seen_discovery.add(key)
        discovery.append({'code': s['code'], 'title': s['title'], 'term': term, 'link': s['link'],
                          'reason': 'Title matches a social impact / environmental criterion. Review description, audience, school, degree level and tags. This is new to the uploaded lists, not necessarily a new university course.', 'decision': 'Pending'})
    counts = defaultdict(int)
    for row in suggestions:
        counts[row['action']] += 1
    return {'term': term, 'suggestions': suggestions, 'discovery': discovery, 'counts': dict(counts),
            'course_count': len(courses), 'schedule_count': len(schedule), 'history_terms': list(history),
            'warnings': ['All results are suggestions. Original spreadsheets are never modified.',
                         'Ridge scores rank possible identity matches; they are not probabilities or proof of an offering.',
                         'No automatic Not Current moves: confirm more than one year of non-offering with complete historical evidence.',
                         'Schedule does not prove course link validity, A/B session, eligibility, or confirmed renumbering. Review those fields.'],
            'model': {k: model[k] for k in ['version', 'method', 'training_records', 'label_source', 'evaluation']}}
