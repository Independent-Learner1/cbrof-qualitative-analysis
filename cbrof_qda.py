"""
CBR-OF qualitative data analysis pipeline
=========================================

Live, reproducible analysis of the Phase 3 stakeholder workshop transcripts for
community-based rehabilitation and prevention care services for obstetric fistula
(CBR-OF), Kenya.

Input : a zip of transcript files (.docx, .txt or .md), in any folder layout.
Output: one zip containing figures, tables (CSV), an Excel coding workbook and a
        Word report.

What runs live on every execution
  1. Text extraction and cleaning of every transcript in the zip.
  2. Segmentation into sentences (the coding unit).
  3. Deductive coding: every sentence is tested against the coding rules of the
     37 child nodes in codebook.py; adjacent coded sentences are merged into
     coding references, as in NVivo.
  4. Quote selection: references are ranked for each node by rule matches,
     TF-IDF similarity to the node definition and length, and the best quotes
     are chosen across different transcripts.
  5. Inductive analysis: non-negative matrix factorisation (NMF) topic modelling
     on all sentences, independent of the codebook, with a topic-to-theme
     alignment matrix as a check on the deductive frame.
  6. NVivo-style queries: coding summary, word frequency, matrix coding
     (theme by transcript), coding coverage, theme co-occurrence.
  7. Optional benchmark: if a manual coding file is supplied, sentence-level
     agreement (Cohen's kappa) between automated and manual coding per theme.

Usage
  python cbrof_qda.py transcripts.zip [--manual manual_coding.csv] [--topics 8] [--out results]
"""

import os, re, sys, json, glob, math, shutil, zipfile, argparse, textwrap, collections, datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import codebook as CB
except ImportError:  # running as a pasted notebook cell: codebook defined in an earlier cell
    CB = sys.modules['__main__']

THEMES = CB.THEMES
NODES = CB.NODES
TH = [t[0] for t in THEMES]
TNAME = {t: n for t, n, o in THEMES}
TOBJ = {t: o for t, n, o in THEMES}
THEME_OF = {k: k.split('.')[0] for k in NODES}
COL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#8a929c', '#b5651d', '#4aa3a2']
INK, MUTED = '#1f2328', '#5f6670'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': '#c9ced4'})
RULES = {k: [(re.compile(p.lstrip('~')), CB.WEAK if p.startswith('~') else 1.0, p.lstrip('~')) for p in v[2]] for k, v in NODES.items()}
EXCLUDE = [re.compile(p) for p in CB.EXCLUDE]


# =============================================================================
# 1. Load and clean
# =============================================================================
def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('…', '...')
    return re.sub(r'[ \t]+', ' ', s)


def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        import docx
        return '\n\n'.join(p.text for p in docx.Document(path).paragraphs)
    return open(path, encoding='utf-8', errors='replace').read()


def load_zip(zip_path, work):
    raw = os.path.join(work, 'raw')
    os.makedirs(raw, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(raw)
    texts = {}
    for p in sorted(glob.glob(os.path.join(raw, '**', '*'), recursive=True)):
        b = os.path.basename(p)
        if b.startswith(('~$', '.')) or b == 'names_to_mask.txt' or os.path.splitext(b)[1].lower() not in ('.docx', '.txt', '.md'):
            continue
        name = os.path.splitext(b)[0]
        lines = [l for l in norm(read_file(p)).split('\n')
                 if l.strip() and 'TurboScribe' not in l and 'longer than 30 minutes' not in l and l.strip() != name]
        texts[name] = '\n'.join(l.strip() for l in lines)
    if not texts:
        raise SystemExit('No .docx, .txt or .md transcripts found in the zip.')
    load_names(*glob.glob(os.path.join(raw, '**', 'names_to_mask.txt'), recursive=True), 'names_to_mask.txt',
               os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.', 'names_to_mask.txt'))
    return texts


def flags(text):
    """Completeness notes detected from the transcript itself."""
    out = []
    if text.lstrip().startswith('...'):
        out.append('opens mid-sentence')
    return out


# =============================================================================
# 2. Segment and code
# =============================================================================
SENT = re.compile(r'(?<=[.?!])\s+(?=[A-Z0-9"\'(])')


def segment(texts):
    rows = []
    for f, t in texts.items():
        i = 0
        for para in t.split('\n'):
            for s in SENT.split(para):
                s = s.strip()
                if s:
                    rows.append({'file': f, 'idx': i, 'text': s, 'words': len(s.split())})
                    i += 1
    return rows


def code_sentence(s):
    low = s.lower()
    if any(p.search(low) for p in EXCLUDE):
        return {}
    out = {}
    for k, rules in RULES.items():
        hits = [(src, w) for p, w, src in rules if p.search(low)]
        if sum(w for _, w in hits) >= CB.MIN_SCORE:
            out[k] = [src for src, _ in hits]
    return out


def code_all(sents):
    for s in sents:
        s['codes'] = code_sentence(s['text']) if s['words'] >= CB.MIN_WORDS else {}
    return sents


def references(sents, key):
    """Merge adjacent sentences coded at the same node (key='node') or theme (key='theme') into references."""
    refs = []
    by_file = collections.defaultdict(list)
    for s in sents:
        by_file[s['file']].append(s)
    for f, ss in by_file.items():
        ss.sort(key=lambda r: r['idx'])
        labels = sorted(NODES) if key == 'node' else TH
        for lab in labels:
            run = []
            for s in ss + [None]:
                hit = s is not None and (lab in s['codes'] if key == 'node' else any(THEME_OF[c] == lab for c in s['codes']))
                if hit and (not run or s['idx'] == run[-1]['idx'] + 1):
                    run.append(s)
                    continue
                if run:
                    hits = sorted({h for r in run for c, hs in r['codes'].items() if (c == lab if key == 'node' else THEME_OF[c] == lab) for h in hs})
                    refs.append({'file': f, key: lab, 'start': run[0]['idx'], 'end': run[-1]['idx'],
                                 'text': ' '.join(r['text'] for r in run), 'hits': hits})
                run = [s] if hit else []
    return refs


# =============================================================================
# 3. Quotes
# =============================================================================
def display(text):
    out = text
    for a, b in CB.CORRECTIONS:
        out = re.sub(r'(?<![A-Za-z])' + re.escape(a) + r'(?![A-Za-z])', '[' + b + ']', out)
    out = TITLED.sub(lambda m: m.group(1) + ' [name]', out)
    for n in NAMES:
        out = re.sub(r'\b' + re.escape(n) + r'\b', '[name]', out)
    return out


TITLED = re.compile(r"\b(Dr\.?|Doctor|Mr\.?|Mrs\.?|Ms\.?|Madam|Prof\.?|Professor|Sister) [A-Z][a-z]+")
NAMES = list(CB.NAME_MASK)


def load_names(*paths):
    for p in paths:
        if p and os.path.isfile(p):
            NAMES.extend(n.strip() for n in open(p, encoding='utf-8') if n.strip() and not n.startswith('#'))


def rank_quotes(node_refs, sents, per_node=3):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    corpus = [s['text'] for s in sents]
    vec = TfidfVectorizer(stop_words='english', sublinear_tf=True, min_df=1).fit(corpus)
    prof = {k: v[0] + ' ' + v[1] + ' ' + ' '.join(re.sub(r'[^a-z ]', ' ', p) for p in v[2]) for k, v in NODES.items()}
    P = vec.transform([prof[k] for k in sorted(NODES)])
    pidx = {k: i for i, k in enumerate(sorted(NODES))}
    R = vec.transform([r['text'] for r in node_refs]) if node_refs else None
    for i, r in enumerate(node_refs):
        sim = float(cosine_similarity(R[i], P[pidx[r['node']]])[0, 0])
        w = len(r['text'].split())
        length = 1.0 if 12 <= w <= 55 else (0.5 if 8 <= w <= 80 else 0.0)
        penalty = 0.5 * max(0, r['text'].count('?') - 1)
        r['similarity'] = round(sim, 3)
        r['score'] = round(len(r['hits']) + 2 * sim + length - penalty, 3)
    best = {}
    for k in sorted(NODES):
        cand = sorted([r for r in node_refs if r['node'] == k and len(r['text'].split()) >= 8], key=lambda r: -r['score'])
        pick, used = [], set()
        for r in cand:  # first pass: different transcripts
            if r['file'] not in used:
                pick.append(r); used.add(r['file'])
            if len(pick) == per_node:
                break
        for r in cand:
            if len(pick) == per_node:
                break
            if r not in pick:
                pick.append(r)
        best[k] = pick
    return best


# =============================================================================
# 4. Queries
# =============================================================================
def word_frequency(texts, top=50):
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    stop = set(ENGLISH_STOP_WORDS) | set(CB.EXTRA_STOP)

    def stem(w):
        for suf, rep in (('ies', 'y'), ('ses', 's'), ('ing', ''), ('ed', ''), ('es', ''), ('s', '')):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                return w[: len(w) - len(suf)] + rep
        return w
    groups = collections.defaultdict(collections.Counter)
    total = 0
    for t in texts.values():
        for w in re.findall(r"[a-z][a-z'\-]+", t.lower()):
            w = w.strip("'-")
            total += 1
            if w in stop or len(w) < 3 or "'" in w:
                continue
            groups[stem(w)][w] += 1
    wf = []
    for c in groups.values():
        n = sum(c.values())
        word = c.most_common(1)[0][0]
        wf.append({'word': word, 'length': len(word), 'count': n, 'weighted_pct': round(100 * n / total, 2), 'similar': ', '.join(sorted(c))})
    wf.sort(key=lambda r: (-r['count'], r['word']))
    return wf[:top], total


def queries(texts, sents, node_refs, theme_refs):
    files = sorted(texts)
    q = {'files': files}
    q['node_refs'] = collections.Counter(r['node'] for r in node_refs)
    q['node_files'] = {k: len({r['file'] for r in node_refs if r['node'] == k}) for k in NODES}
    q['theme_refs'] = collections.Counter(r['theme'] for r in theme_refs)
    q['theme_files'] = {t: len({r['file'] for r in theme_refs if r['theme'] == t}) for t in TH}
    q['file_refs'] = collections.Counter(r['file'] for r in theme_refs)
    q['matrix_file'] = {(t, f): sum(1 for r in theme_refs if r['theme'] == t and r['file'] == f) for t in TH for f in files}
    chars = {f: len(texts[f]) for f in files}
    q['coverage'] = {(t, f): round(100 * sum(len(s['text']) for s in sents if s['file'] == f and any(THEME_OF[c] == t for c in s['codes'])) / max(chars[f], 1), 2)
                     for t in TH for f in files}
    co = collections.Counter()
    for s in sents:
        ths = sorted({THEME_OF[c] for c in s['codes']})
        for i in range(len(ths)):
            for j in range(i + 1, len(ths)):
                co[(ths[i], ths[j])] += 1
    q['cooccur'] = co
    q['words'] = {f: len(texts[f].split()) for f in files}
    q['coded_sentences'] = sum(1 for s in sents if s['codes'])
    q['eligible_sentences'] = sum(1 for s in sents if s['words'] >= CB.MIN_WORDS)
    return q


# =============================================================================
# 5. Inductive topic model
# =============================================================================
def topic_model(sents, k=8, seed=1):
    from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
    from sklearn.decomposition import NMF
    docs = [s for s in sents if s['words'] >= 8]
    stop = list(set(ENGLISH_STOP_WORDS) | set(CB.EXTRA_STOP) | {'fistula', 'obstetric', 'don', 'doesn', 'didn', 'isn', 'wasn', 'aren', 'couldn', 'won', 'shouldn', 'guys', 'presentation', 'discuss', 'talking', 'talk', 'shall', 'coming'})
    vec = TfidfVectorizer(stop_words=stop, min_df=2, max_df=0.5, ngram_range=(1, 2), token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]{2,}\b', sublinear_tf=True)
    X = vec.fit_transform([d['text'] for d in docs])
    model = NMF(n_components=k, random_state=seed, init='nndsvda', max_iter=600)
    W = model.fit_transform(X)
    H = model.components_
    terms = np.array(vec.get_feature_names_out())
    dom = W.argmax(1)
    strength = W.max(1)
    topics = []
    for i in range(k):
        members = [j for j in range(len(docs)) if dom[j] == i and strength[j] > 0]
        top_terms = list(terms[H[i].argsort()[::-1][:10]])
        rep = sorted(members, key=lambda j: -W[j, i])[:3]
        align = {t: (sum(1 for j in members if any(THEME_OF[c] == t for c in docs[j]['codes'])) / len(members) if members else 0) for t in TH}
        topics.append({'topic': f'Topic {i + 1}', 'terms': top_terms, 'size': len(members),
                       'examples': [(docs[j]['file'], docs[j]['text']) for j in rep], 'alignment': align,
                       'best_theme': max(align, key=align.get) if members else ''})
    return topics


# =============================================================================
# 6. Benchmark against manual coding (optional)
# =============================================================================
def benchmark(sents, manual_csv):
    """manual_csv columns: file, excerpt, nodes (semicolon separated). Sentence-level agreement per theme."""
    import csv
    man = collections.defaultdict(set)
    for row in csv.DictReader(open(manual_csv, encoding='utf-8')):
        ex = norm(row['excerpt']).strip()
        themes = {n.strip().split('.')[0] for n in row['nodes'].split(';') if n.strip()}
        for s in sents:
            if s['file'] == row['file'] and (s['text'] in ex or ex in s['text']):
                man[(s['file'], s['idx'])] |= themes
    rows = []
    elig = [s for s in sents if s['words'] >= CB.MIN_WORDS]
    for t in TH:
        a = np.array([t in man.get((s['file'], s['idx']), set()) for s in elig])
        b = np.array([any(THEME_OF[c] == t for c in s['codes']) for s in elig])
        tp, fp, fn = int((a & b).sum()), int((~a & b).sum()), int((a & ~b).sum())
        tn = len(elig) - tp - fp - fn
        po = (tp + tn) / len(elig)
        pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / len(elig) ** 2
        kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
        rows.append({'theme': t, 'manual': int(a.sum()), 'auto': int(b.sum()), 'agree': tp,
                     'recall': round(tp / max(a.sum(), 1), 2), 'precision': round(tp / max(b.sum(), 1), 2), 'kappa': round(kappa, 2)})
    return rows


# =============================================================================
# 7. Figures
# =============================================================================
def _save(fig, out, name):
    p = os.path.join(out, name)
    fig.savefig(p, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    return p


def fig_hierarchy(q, out):
    import squarify
    fig, ax = plt.subplots(figsize=(11, 6.6), dpi=200)
    order = sorted([t for t in TH if q['theme_refs'][t]], key=lambda t: -q['theme_refs'][t])
    rects = squarify.padded_squarify(squarify.normalize_sizes([q['theme_refs'][t] for t in order], 1000, 600), 0, 0, 1000, 600)
    for t, r in zip(order, rects):
        ci = TH.index(t)
        kids = sorted([k for k in NODES if THEME_OF[k] == t and q['node_refs'][k]], key=lambda k: -q['node_refs'][k])
        x, y, dx, dy = r['x'] + 3, r['y'] + 3, r['dx'] - 6, r['dy'] - 6
        head = 34
        ax.add_patch(plt.Rectangle((x, y + dy - head), dx, head, color=COL[ci], lw=0))
        ax.text(x + 6, y + dy - head / 2, f'{TNAME[t]} ({q["theme_refs"][t]})', color='white', fontsize=7.4, fontweight='bold', va='center', clip_on=True)
        if not kids:
            continue
        ks = [q['node_refs'][k] for k in kids]
        for k, s in zip(kids, squarify.padded_squarify(squarify.normalize_sizes(ks, dx, dy - head), x, y, dx, dy - head)):
            ax.add_patch(plt.Rectangle((s['x'] + 1.5, s['y'] + 1.5), s['dx'] - 3, s['dy'] - 3, color=COL[ci], alpha=0.22 + 0.5 * q['node_refs'][k] / max(ks), lw=0))
            if s['dx'] > 95 and s['dy'] > 60:
                lines = textwrap.wrap(NODES[k][0], max(8, int(s['dx'] / 6.4)))[:3]
                ax.text(s['x'] + 6, s['y'] + s['dy'] - 8, '\n'.join(lines) + f'\n({q["node_refs"][k]})', fontsize=6.2, color=INK, va='top', clip_on=True)
            else:
                ax.text(s['x'] + s['dx'] / 2, s['y'] + s['dy'] / 2, f'{k}\n({q["node_refs"][k]})', fontsize=6, color=INK, va='center', ha='center', clip_on=True)
    ax.set_xlim(0, 1000); ax.set_ylim(0, 600); ax.axis('off')
    return _save(fig, out, 'fig01_hierarchy_chart.png')


def fig_nodes(q, out):
    items = [(k, q['node_refs'][k]) for t in TH for k in sorted([k for k in NODES if THEME_OF[k] == t], key=lambda k: -q['node_refs'][k])]
    fig, ax = plt.subplots(figsize=(9, 10), dpi=200)
    y = np.arange(len(items))[::-1]
    ax.barh(y, [n for _, n in items], color=[COL[TH.index(THEME_OF[k])] for k, _ in items], height=0.7)
    for yy, (k, n) in zip(y, items):
        ax.text(n + 0.3, yy, str(n), va='center', fontsize=7.5, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([f'{k}  {NODES[k][0]}' for k, _ in items], fontsize=7.2)
    ax.set_xlabel('Coding references', color=MUTED); ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.grid(True, color='#eceef1'); ax.set_axisbelow(True)
    from matplotlib.ticker import MaxNLocator
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=COL[i]) for i in range(len(TH))], [TNAME[t] for t in TH], fontsize=7, loc='lower right', frameon=True, framealpha=0.95)
    return _save(fig, out, 'fig02_node_references.png')


def fig_wordfreq(wf, out):
    top = wf[:20][::-1]
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    ax.barh([r['word'] for r in top], [r['count'] for r in top], color='#2a78d6', height=0.65)
    for i, r in enumerate(top):
        ax.text(r['count'] + 1, i, str(r['count']), va='center', fontsize=8, color=INK)
    ax.set_xlabel('Count (stemmed, stop words removed)', color=MUTED); ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.grid(True, color='#eceef1'); ax.set_axisbelow(True)
    return _save(fig, out, 'fig03_word_frequency.png')


def fig_wordcloud(wf, out):
    from wordcloud import WordCloud
    freqs = {r['word']: r['count'] for r in wf}
    order = list(freqs)
    wc = WordCloud(width=1800, height=900, background_color='white', prefer_horizontal=0.9, max_words=100, random_state=7,
                   color_func=lambda word, **kw: COL[order.index(word) % 7] if order.index(word) < 14 else '#5f6670').generate_from_frequencies(freqs)
    fig = plt.figure(figsize=(10, 5), dpi=200); plt.imshow(wc, interpolation='bilinear'); plt.axis('off')
    return _save(fig, out, 'fig04_word_cloud.png')


def _heat(M, rows, cols, cmap, fmt, out, name, size):
    fig, ax = plt.subplots(figsize=size, dpi=200)
    vmax = max(M.max(), 1e-9)
    ax.imshow(M, cmap=cmap, aspect='auto', vmin=0, vmax=vmax * 1.1)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            ax.text(j, i, fmt(v) if v else '', ha='center', va='center', fontsize=8, color='white' if v > vmax * 0.55 else INK)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=7.5)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=8)
    ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
    return _save(fig, out, name)


def fig_matrix(q, out):
    files = q['files']
    short = [re.sub(r'^Z0+', 'Z', f) for f in files]
    M = np.array([[q['matrix_file'][(t, f)] for f in files] for t in TH], dtype=float)
    a = _heat(M, [TNAME[t] for t in TH], short, 'Blues', lambda v: f'{int(v)}', out, 'fig05_matrix_theme_by_file.png', (11, 4.6))
    C = np.array([[q['coverage'][(t, f)] for f in files] for t in TH])
    b = _heat(C, [TNAME[t] for t in TH], short, 'Oranges', lambda v: f'{v:.1f}', out, 'fig06_coverage_by_file.png', (11, 4.6))
    return a, b


def fig_cooccur(q, out):
    fig, ax = plt.subplots(figsize=(10, 7.0), dpi=200)
    n = len(TH)
    pos = {t: (math.cos(math.pi / 2 - 2 * math.pi * i / n), math.sin(math.pi / 2 - 2 * math.pi * i / n)) for i, t in enumerate(TH)}
    mx = max(q['cooccur'].values() or [1])
    lab_min = sorted(q['cooccur'].values(), reverse=True)[min(7, len(q['cooccur']) - 1)] if q['cooccur'] else 0
    for (a, b), v in sorted(q['cooccur'].items(), key=lambda x: x[1]):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        ax.plot([x1, x2], [y1, y2], color='#8a929c', lw=0.6 + 5 * v / mx, alpha=0.3 + 0.5 * v / mx, zorder=1, solid_capstyle='round')
        if v >= lab_min:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, str(v), fontsize=7.5, ha='center', va='center', zorder=3,
                    bbox=dict(boxstyle='round,pad=0.18', fc='white', ec='#c9ced4', lw=0.5))
    mr = max(q['theme_refs'].values() or [1])
    for i, t in enumerate(TH):
        x, y = pos[t]
        r = 0.09 + 0.11 * q['theme_refs'][t] / mr
        ax.add_patch(plt.Circle((x, y), r, color=COL[i], zorder=2))
        ax.text(x, y, f'{t}\n{q["theme_refs"][t]}', ha='center', va='center', color='white', fontsize=8.5, fontweight='bold', zorder=4)
        lab = '\n'.join(textwrap.wrap(TNAME[t], 22))
        if abs(x) < 0.3:
            ax.text(x, y + (r + 0.05) * (1 if y > 0 else -1), lab, ha='center', va='bottom' if y > 0 else 'top', fontsize=8, color=INK)
        else:
            ax.text(x + (r + 0.05) * (1 if x > 0 else -1), y, lab, ha='left' if x > 0 else 'right', va='center', fontsize=8, color=INK)
    ax.set_xlim(-2.1, 2.1); ax.set_ylim(-1.45, 1.5); ax.set_aspect('equal'); ax.axis('off')
    return _save(fig, out, 'fig07_theme_cooccurrence.png')


def fig_topics(topics, out):
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(topics) + 1.2), dpi=200)
    y = np.arange(len(topics))[::-1]
    ax.barh(y, [t['size'] for t in topics], color=[COL[TH.index(t['best_theme'])] if t['best_theme'] else '#8a929c' for t in topics], height=0.62)
    for yy, t in zip(y, topics):
        ax.text(t['size'] + 1, yy, ', '.join(t['terms'][:6]), va='center', fontsize=7.6, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([t['topic'] for t in topics], fontsize=8)
    ax.set_xlabel('Sentences (dominant topic)', color=MUTED); ax.spines[['top', 'right']].set_visible(False)
    ax.set_xlim(0, max(t['size'] for t in topics) * 2.4)
    return _save(fig, out, 'fig08_topic_model.png')


def fig_alignment(topics, out):
    M = np.array([[100 * t['alignment'][th] for th in TH] for t in topics])
    return _heat(M, [t['topic'] for t in topics], TH, 'Greens', lambda v: f'{v:.0f}', out, 'fig09_topic_theme_alignment.png', (7.5, 0.45 * len(topics) + 1.4))


# =============================================================================
# 8. Excel workbook
# =============================================================================
def workbook(path, texts, sents, node_refs, best, q, wf, topics, bench):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.utils import get_column_letter
    wb = Workbook(); wb.remove(wb.active)
    HF, HFont, B = PatternFill('solid', fgColor='2A78D6'), Font(bold=True, color='FFFFFF', name='Arial', size=10), Font(name='Arial', size=10)

    def sheet(name, header, rows, widths, wrap=()):
        ws = wb.create_sheet(name); ws.append(header)
        for c in ws[1]:
            c.fill, c.font, c.alignment = HF, HFont, Alignment(vertical='center', wrap_text=True)
        for r in rows:
            ws.append(r)
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font, c.alignment = B, Alignment(vertical='top', wrap_text=c.column in wrap)
        for i, w in enumerate(widths):
            ws.column_dimensions[get_column_letter(i + 1)].width = w
        ws.freeze_panes = 'A2'
        if rows:
            ws.auto_filter.ref = ws.dimensions
        return ws
    ws = wb.create_sheet('README')
    for line in ['CBR-OF Phase 3 workshop transcripts: automated qualitative coding workbook.',
                 f'Generated {datetime.date.today().isoformat()} by cbrof_qda.py from {len(texts)} transcripts.',
                 'Coding is rule-based (codebook.py) at sentence level; adjacent coded sentences are merged into references, as in NVivo.',
                 'Quotes show transcription corrections in square brackets and personal names masked as [name].',
                 'Automated coding is a first pass. Review the Coded references sheet and refine the rules before publication.']:
        ws.append([line])
    ws.column_dimensions['A'].width = 130
    sheet('Files', ['File', 'Words', 'Sentences', 'Coded sentences', 'Theme references', 'Notes'],
          [[f, q['words'][f], sum(1 for s in sents if s['file'] == f), sum(1 for s in sents if s['file'] == f and s['codes']), q['file_refs'][f], '; '.join(flags(texts[f]))] for f in q['files']],
          [12, 9, 11, 15, 16, 30])
    rows = []
    for t, n, o in THEMES:
        rows.append([t, 'Theme', n, o, '', q['theme_files'][t], q['theme_refs'][t]])
        rows += [[k, 'Child node', NODES[k][0], NODES[k][1], ' | '.join(NODES[k][2]), q['node_files'][k], q['node_refs'][k]] for k in NODES if THEME_OF[k] == t]
    ws = sheet('Codebook', ['Node', 'Level', 'Name', 'Definition / objective', 'Coding rules (regex)', 'Files', 'References'], rows, [8, 11, 42, 60, 60, 7, 11], wrap=(3, 4, 5))
    for row in ws.iter_rows(min_row=2):
        if row[1].value == 'Theme':
            for c in row:
                c.font, c.fill = Font(bold=True, name='Arial', size=10), PatternFill('solid', fgColor='E4EEFB')
    sheet('Coded references', ['Ref', 'File', 'Node', 'Node name', 'Theme', 'Sentences', 'Text (as transcribed)', 'Quote (corrected, names masked)', 'Matched rules', 'Similarity', 'Score'],
          [[i + 1, r['file'], r['node'], NODES[r['node']][0], THEME_OF[r['node']], f"{r['start'] + 1}-{r['end'] + 1}", r['text'], display(r['text']), ' | '.join(r['hits']), r.get('similarity'), r.get('score')]
           for i, r in enumerate(node_refs)], [6, 11, 7, 34, 7, 10, 60, 60, 40, 10, 8], wrap=(7, 8, 9))
    sheet('Selected quotes', ['Node', 'Node name', 'Rank', 'File', 'Quote', 'Score'],
          [[k, NODES[k][0], i + 1, r['file'], display(r['text']), r['score']] for k in sorted(NODES) for i, r in enumerate(best[k])], [7, 36, 6, 11, 90, 8], wrap=(5,))
    sheet('Sentence coding', ['File', 'Sentence', 'Text', 'Nodes', 'Themes'],
          [[s['file'], s['idx'] + 1, s['text'], '; '.join(sorted(s['codes'])), '; '.join(sorted({THEME_OF[c] for c in s['codes']}))] for s in sents if s['codes']],
          [11, 9, 90, 20, 14], wrap=(3,))
    files = q['files']
    ws = sheet('Matrix theme x file', ['Theme'] + files + ['Total'],
               [[f'{t} {TNAME[t]}'] + [q['matrix_file'][(t, f)] for f in files] + [f'=SUM(B{i + 2}:{get_column_letter(len(files) + 1)}{i + 2})'] for i, t in enumerate(TH)],
               [52] + [11] * (len(files) + 1))
    ws.conditional_formatting.add(f'B2:{get_column_letter(len(files) + 1)}{len(TH) + 1}', ColorScaleRule(start_type='min', start_color='F7FBFF', end_type='max', end_color='08519C'))
    ws = sheet('Coverage %', ['Theme'] + files, [[f'{t} {TNAME[t]}'] + [q['coverage'][(t, f)] for f in files] for t in TH], [52] + [11] * len(files))
    ws.conditional_formatting.add(f'B2:{get_column_letter(len(files) + 1)}{len(TH) + 1}', ColorScaleRule(start_type='min', start_color='FFF5EB', end_type='max', end_color='A63603'))
    sheet('Co-occurrence', [''] + TH, [[a] + [None if a == b else q['cooccur'].get(tuple(sorted((a, b))), 0) for b in TH] for a in TH], [8] * (len(TH) + 1))
    sheet('Word frequency', ['Word', 'Length', 'Count', 'Weighted percentage (%)', 'Similar words'], [[w['word'], w['length'], w['count'], w['weighted_pct'], w['similar']] for w in wf], [16, 9, 9, 22, 50])
    sheet('Topics (inductive)', ['Topic', 'Sentences', 'Top terms', 'Best-aligned theme'] + [f'% coded {t}' for t in TH] + ['Example 1', 'Example 2'],
          [[t['topic'], t['size'], ', '.join(t['terms']), t['best_theme']] + [round(100 * t['alignment'][th]) for th in TH] + [display(e[1]) for e in t['examples'][:2]] + [''] * (2 - len(t['examples'][:2])) for t in topics],
          [9, 10, 50, 12] + [10] * len(TH) + [60, 60], wrap=(3, 12, 13))
    if bench:
        sheet('Benchmark', ['Theme', 'Manual sentences', 'Auto sentences', 'Both', 'Recall', 'Precision', "Cohen's kappa"],
              [[b['theme'], b['manual'], b['auto'], b['agree'], b['recall'], b['precision'], b['kappa']] for b in bench], [10, 16, 14, 8, 9, 10, 13])
    sheet('Corrections', ['As transcribed', 'Shown in quotations as'], [[a, f'[{b}]'] for a, b in CB.CORRECTIONS], [28, 34])
    wb.save(path)
    return wb


# =============================================================================
# 9. Word report
# =============================================================================
def report(path, texts, sents, node_refs, theme_refs, best, q, wf, total_words, topics, bench, figs):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    doc = Document()
    st = doc.styles['Normal']; st.font.name = 'Times New Roman'; st.font.size = Pt(11.5)
    st.paragraph_format.space_after = Pt(6)
    for s in ('Heading 1', 'Heading 2'):
        doc.styles[s].font.name = 'Times New Roman'; doc.styles[s].font.color.rgb = RGBColor(0x1F, 0x23, 0x28)
    doc.styles['Heading 1'].font.size = Pt(14); doc.styles['Heading 2'].font.size = Pt(12)
    sec = doc.sections[0]; sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for m in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(sec, m, Cm(2.3))
    n = {'fig': 0, 'tab': 0}

    def para(text, bold=False, italic=False, size=None, align=None, keep=False, after=None):
        p = doc.add_paragraph(); r = p.add_run(text); r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
        if align == 'c': p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if align == 'j': p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if keep: p.paragraph_format.keep_with_next = True
        if after is not None: p.paragraph_format.space_after = Pt(after)
        return p

    def shade(cell, fill):
        sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), fill)
        cell._tc.get_or_add_tcPr().append(sh)

    def table(caption, header, rows, widths, size=9):
        n['tab'] += 1
        para(f'Table {n["tab"]}: {caption}', bold=True, size=10.5, keep=True, after=3)
        t = doc.add_table(rows=1, cols=len(header)); t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); t._tbl.tblPr.append(lay)
        for i, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
            gc.set(qn('w:w'), str(int(widths[i] * 567)))
        for i, h in enumerate(header):
            c = t.rows[0].cells[i]; c.text = ''; r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(size); r.font.color.rgb = RGBColor(255, 255, 255); shade(c, '2A78D6')
        for k, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ''; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
                if k % 2: shade(cells[i], 'F3F5F8')
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def figure(caption, p, width=16, note=None):
        n['fig'] += 1
        para(f'Figure {n["fig"]}: {caption}', bold=True, size=10.5, keep=True, after=3)
        pp = doc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER; pp.add_run().add_picture(p, width=Cm(width))
        if note: para(note, size=9)

    def quote(r):
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(1); p.paragraph_format.right_indent = Cm(0.6); p.paragraph_format.space_after = Pt(5)
        a = p.add_run('“' + display(r['text']) + '” '); a.italic = True; a.font.size = Pt(10.5)
        b = p.add_run(f'({r["file"]})'); b.font.size = Pt(9.5)

    nfiles, nnode = len(texts), len(NODES)
    order = sorted(TH, key=lambda t: -q['theme_refs'][t])
    para('Automated Thematic Analysis of the Phase 3 Stakeholder Workshop Transcripts', bold=True, size=16, align='c', after=4)
    para('Community-Based Rehabilitation and Prevention Care Services for Obstetric Fistula (CBR-OF), Kenya', italic=True, align='c', after=4)
    para(f'Generated by cbrof_qda.py on {datetime.date.today().strftime("%d %B %Y")}', size=10, align='c', after=14)

    doc.add_heading('1. Summary', level=1)
    para(f'{nfiles} transcripts ({total_words:,} words, {len(sents):,} sentences) were coded automatically against a codebook of {len(TH)} themes and {nnode} child nodes. '
         f'{q["coded_sentences"]:,} of {q["eligible_sentences"]:,} eligible sentences ({100 * q["coded_sentences"] / max(q["eligible_sentences"], 1):.0f}%) were coded, giving {len(node_refs):,} node references '
         f'and {sum(q["theme_refs"].values()):,} theme references. The most coded themes were ' +
         '; '.join(f'{TNAME[t]} ({q["theme_refs"][t]} references in {q["theme_files"][t]} files)' for t in order[:3]) + '.', align='j')
    top_nodes = sorted(NODES, key=lambda k: -q['node_refs'][k])[:5]
    para('The five most coded child nodes were ' + '; '.join(f'{k} {NODES[k][0]} ({q["node_refs"][k]})' for k in top_nodes) + '.', align='j')

    doc.add_heading('2. Methods', level=1)
    para('Transcripts were extracted from the uploaded zip, cleaned of transcription service banners, and split into sentences, which formed the coding unit. '
         f'Sentences shorter than {CB.MIN_WORDS} words were not coded. Each sentence was tested against the coding rules of every child node (regular expressions defined in codebook.py, '
         'derived deductively from the three workshop objectives and refined against the transcripts). Specific rules scored 1 and broad rules scored '
         f'{CB.WEAK}; a sentence was coded at a node when its score reached {CB.MIN_SCORE}, and a sentence could be coded at several nodes. Sentences that matched facilitation patterns '
         '(for example, references to the session, sticky notes or earlier study phases) were not coded. Adjacent sentences coded at the same node were merged into one reference, as NVivo does with contiguous coded text.', align='j')
    para('For each node, references were ranked by the number of distinct rules matched, their TF-IDF cosine similarity to the node name and definition, and a length criterion (12 to 55 words preferred); '
         'the highest ranked references from different transcripts were selected as illustrative quotes. As an inductive check that does not depend on the codebook, non-negative matrix factorisation (NMF) '
         f'was run on all sentences of 8 or more words to extract {len(topics)} topics, and each topic was aligned to the theme most often coded in its sentences. '
         'Quotes show transcription corrections in square brackets and personal names masked as [name].', align='j')
    para('Automated rule-based coding detects what is said in the vocabulary of the rules; it does not interpret meaning, irony or context, and it cannot attribute speakers because the transcripts are not speaker-labelled. '
         'The output is a structured first pass that should be reviewed, and the rules refined, by the research team.', italic=True, size=10.5, align='j')

    doc.add_heading('3. Data sources', level=1)
    table('Transcripts Analysed', ['File', 'Words', 'Sentences', 'Coded sentences', 'Theme refs', 'Notes'],
          [[f, f'{q["words"][f]:,}', sum(1 for s in sents if s['file'] == f), sum(1 for s in sents if s['file'] == f and s['codes']), q['file_refs'][f], '; '.join(flags(texts[f]))] for f in q['files']]
          + [['Total', f'{total_words:,}', len(sents), q['coded_sentences'], sum(q['file_refs'].values()), '']], [2.4, 2.0, 2.2, 2.8, 2.2, 4.8])

    doc.add_heading('4. Coding structure', level=1)
    table('Coding Summary by Theme', ['ID', 'Theme', 'Objective', 'Files', 'Refs'],
          [[t, TNAME[t], TOBJ[t], q['theme_files'][t], q['theme_refs'][t]] for t in TH], [1.0, 6.4, 5.4, 1.6, 1.6])
    figure('Hierarchy Chart of Themes and Child Nodes, Sized by Coding References', figs['hierarchy'], 16.4,
           'Note: Small tiles are labelled by node ID; full names are in Appendix A.')
    figure('Coding References by Child Node', figs['nodes'], 14.5)

    doc.add_heading('5. Word frequency', level=1)
    table('Word Frequency Query: 30 Most Frequent Words', ['Word', 'Length', 'Count', 'Weighted %', 'Similar words'],
          [[w['word'], w['length'], w['count'], f'{w["weighted_pct"]:.2f}', w['similar']] for w in wf[:30]], [3.0, 1.6, 1.6, 2.0, 7.8])
    figure('Word Frequency Chart: 20 Most Frequent Words', figs['wordfreq'], 13.5)
    figure('Word Cloud of the Most Frequent Words', figs['wordcloud'], 15.5)

    doc.add_heading('6. Matrix coding, coverage and co-occurrence', level=1)
    figure('Matrix Coding Query: Theme References by Transcript', figs['matrix'], 16.4)
    figure('Coding Coverage (% of Characters) by Theme and Transcript', figs['coverage'], 16.4)
    co = sorted(q['cooccur'].items(), key=lambda x: -x[1])[:3]
    figure('Theme Co-occurrence Network', figs['cooccur'], 15,
           'Note: Circle size reflects theme references; line thickness reflects sentences coded at both themes. Strongest links: ' +
           '; '.join(f'{a} and {b} ({v})' for (a, b), v in co) + '.')

    doc.add_heading('7. Findings by theme', level=1)
    for t in TH:
        doc.add_heading(f'{t} {TNAME[t]}', level=2)
        kids = sorted([k for k in NODES if THEME_OF[k] == t], key=lambda k: -q['node_refs'][k])
        para(f'{q["theme_refs"][t]} references in {q["theme_files"][t]} of {nfiles} transcripts ({TOBJ[t]}). Child nodes: ' +
             '; '.join(f'{NODES[k][0]} ({q["node_refs"][k]})' for k in kids) + '.', align='j')
        for k in kids:
            if not best[k]:
                continue
            para(f'{k} {NODES[k][0]}', bold=True, size=10.5, keep=True, after=2)
            for r in best[k][:2]:
                quote(r)

    doc.add_heading('8. Inductive topics', level=1)
    para('Topics were extracted without reference to the codebook. Strong alignment between a topic and a theme supports the deductive frame; a topic that aligns weakly with every theme '
         'points to content the codebook may be missing.', align='j')
    table('Topics from Non-negative Matrix Factorisation', ['Topic', 'Sentences', 'Top terms', 'Best-aligned theme'],
          [[t['topic'], t['size'], ', '.join(t['terms'][:8]), f'{t["best_theme"]} ({100 * t["alignment"].get(t["best_theme"], 0):.0f}%)' if t['best_theme'] else ''] for t in topics], [1.8, 2.0, 9.4, 3.2])
    figure('Topic Sizes and Top Terms', figs['topics'], 15.5, 'Note: Bars are coloured by the best-aligned theme, using the theme colours of Figures 1 and 2.')
    figure('Topic to Theme Alignment (% of Topic Sentences Coded at Each Theme)', figs['alignment'], 12)

    if bench:
        doc.add_heading('9. Agreement with manual coding', level=1)
        table("Sentence-level Agreement between Automated and Manual Coding", ['Theme', 'Manual', 'Auto', 'Both', 'Recall', 'Precision', 'Kappa'],
              [[b['theme'], b['manual'], b['auto'], b['agree'], b['recall'], b['precision'], b['kappa']] for b in bench], [2.0, 2.0, 2.0, 2.0, 2.2, 2.4, 2.2])

    doc.add_heading('Limitations', level=1)
    para('Rule-based coding is transparent and reproducible but literal: it misses ideas expressed in words the rules do not anticipate and can code sentences that use a rule word in another sense. '
         'Reference counts measure how often a topic was raised, not its importance. Speaker roles are not available from unlabelled transcripts. Automated transcription errors affect both coding and quotes. '
         'Transcripts cut short by the transcription service, or that open mid-sentence, are incomplete. Every selected quote should be checked against the audio before publication.', align='j')

    doc.add_page_break()
    doc.add_heading('Appendix A: Codebook and coding rules', level=1)
    rows = []
    for t in TH:
        rows.append([t, TNAME[t], TOBJ[t], '', q['theme_refs'][t]])
        rows += [[k, NODES[k][0], NODES[k][1], ' | '.join(NODES[k][2]), q['node_refs'][k]] for k in NODES if THEME_OF[k] == t]
    table('Codebook', ['Node', 'Name', 'Definition', 'Rules', 'Refs'], rows, [1.2, 3.6, 5.2, 5.4, 1.2], size=7.5)
    doc.save(path)


# =============================================================================
# 10. Run
# =============================================================================
def run(zip_path, out_dir='CBR-OF_QDA_Results', manual=None, n_topics=8):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    figdir, tabdir = os.path.join(out_dir, 'figures'), os.path.join(out_dir, 'tables')
    os.makedirs(figdir); os.makedirs(tabdir)
    work = os.path.join(out_dir, '_work')
    print('1/7 Loading transcripts ...')
    texts = load_zip(zip_path, work)
    print('    ', ', '.join(f'{k} ({len(v.split()):,} words)' for k, v in texts.items()))
    print('2/7 Segmenting and coding ...')
    sents = code_all(segment(texts))
    node_refs, theme_refs = references(sents, 'node'), references(sents, 'theme')
    print(f'     {len(sents):,} sentences, {sum(1 for s in sents if s["codes"]):,} coded, {len(node_refs):,} node references')
    print('3/7 Selecting quotes ...')
    best = rank_quotes(node_refs, sents)
    print('4/7 Running queries ...')
    q = queries(texts, sents, node_refs, theme_refs)
    wf, total_words = word_frequency(texts)
    print('5/7 Topic modelling ...')
    topics = topic_model(sents, k=n_topics)
    bench = benchmark(sents, manual) if manual else None
    print('6/7 Drawing figures ...')
    figs = {'hierarchy': fig_hierarchy(q, figdir), 'nodes': fig_nodes(q, figdir), 'wordfreq': fig_wordfreq(wf, figdir), 'wordcloud': fig_wordcloud(wf, figdir),
            'cooccur': fig_cooccur(q, figdir), 'topics': fig_topics(topics, figdir), 'alignment': fig_alignment(topics, figdir)}
    figs['matrix'], figs['coverage'] = fig_matrix(q, figdir)
    print('7/7 Writing workbook, tables and report ...')
    xlsx = os.path.join(out_dir, 'CBR-OF_Coding_Workbook.xlsx')
    wb = workbook(xlsx, texts, sents, node_refs, best, q, wf, topics, bench)
    import csv
    for ws in wb.worksheets:
        if ws.title == 'README':
            continue
        with open(os.path.join(tabdir, re.sub(r'[^A-Za-z0-9]+', '_', ws.title).strip('_') + '.csv'), 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            for row in ws.iter_rows(values_only=True):
                w.writerow(['' if (v is None or str(v).startswith('=')) else v for v in row])
    report(os.path.join(out_dir, 'CBR-OF_Thematic_Analysis_Report.docx'), texts, sents, node_refs, theme_refs, best, q, wf, total_words, topics, bench, figs)
    json.dump({'files': q['files'], 'theme_refs': dict(q['theme_refs']), 'node_refs': dict(q['node_refs']), 'cooccur': {f'{a}|{b}': v for (a, b), v in q['cooccur'].items()},
               'topics': [{k: v for k, v in t.items() if k != 'examples'} for t in topics], 'benchmark': bench},
              open(os.path.join(out_dir, 'summary.json'), 'w'), indent=1)
    shutil.rmtree(work)
    zip_out = shutil.make_archive(out_dir, 'zip', root_dir=os.path.dirname(os.path.abspath(out_dir)), base_dir=os.path.basename(out_dir))
    print('Done. Theme references:', {t: q['theme_refs'][t] for t in TH})
    print('Results:', zip_out)
    return zip_out


if __name__ == '__main__' and 'ipykernel' not in sys.modules:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('zip', help='zip file of transcripts (.docx, .txt or .md)')
    ap.add_argument('--manual', help='optional CSV of manual coding (file, excerpt, nodes) for benchmarking')
    ap.add_argument('--topics', type=int, default=8, help='number of inductive topics (default 8)')
    ap.add_argument('--out', default='CBR-OF_QDA_Results', help='output folder name')
    a = ap.parse_args()
    run(a.zip, a.out, a.manual, a.topics)
