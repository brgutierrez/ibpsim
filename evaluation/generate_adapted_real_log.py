"""
generate_adapted_real_log.py
============================
Step 2 of the pipeline. Builds the "adapted real-world log": 30 reference logs
(one per replicate) drawn from the single multi-year real-world log, so that the
reference of every replicate covers a period comparable to that of the simulated
logs (see Section 5.1.2 of the article).

Procedure of ``--mode window_systematic`` (the one used in the article):

  1. Anchor. Replicate r is anchored at the start instant and span (18-35 days)
     of the Planner-only simulated log of the same replicate (<planner-only-dir>/<r>/merged_log.xes).
  2. Window. The period covered by the arrivals of the real log is divided into
     R = 30 equally spaced starting points (about 13 days apart). Replicate r uses
     the window that starts at the r-th point and is as long as the simulated log
     of that replicate. Since the windows are longer than the spacing between
     starting points, consecutive windows may partially overlap.
  3. Sampling. N = 20 cases whose first event falls in the window are sampled
     without replacement. If the window contains fewer than 20 cases (this
     happens only for replicate 1: 6 cases) the sample is completed by drawing
     cases with replacement, so that case repetitions occur in that replicate.
  4. Alignment. All the timestamps are shifted so that the window starts at the
     anchor instant of the simulated log (case durations are preserved).

The sampling is driven by ``random.Random(--seed)`` (default 2021), so the same
inputs give the same output. The other modes (window, resample, compress) were
explored during the study and are not used in the article.

Inputs : the real-world log (XES) and the Planner-only simulated logs.
Output : <output-dir>/<r>/merged_log.xes and <output-dir>/generation_report.csv

Usage:
    python generate_adapted_real_log.py --real-log data/logReal.xes \
        --planner-only-dir data/logOro --output-dir data/logRealAdaptado
"""

import argparse
import csv
import os
import random
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timedelta
from statistics import mean, median


HERE           = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(HERE, 'data')

TS_KEYS        = {'time:timestamp', 'start_time', 'end_time'}
N_TRACES       = 20


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_xes(path):
    tree = ET.parse(path)
    root = tree.getroot()
    traces = [c for c in root if c.tag.endswith('trace')]
    return tree, root, traces


def _parse_ts(raw):
    raw = raw.replace('Z', '+00:00')
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is not None:
        offset = dt.utcoffset()
        dt = (dt - offset).replace(tzinfo=None)
    return dt


def _fmt_ts(dt):
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def get_trace_timestamps(trace):
    ts = []
    for ev in [c for c in trace if c.tag.endswith('event')]:
        for attr in ev:
            if attr.get('key') in TS_KEYS:
                try:
                    ts.append(_parse_ts(attr.get('value', '')))
                except Exception:
                    pass
    return ts


def build_trace_index(traces):
    index = []
    for trace in traces:
        ts = get_trace_timestamps(trace)
        if ts:
            index.append((min(ts), trace))
    index.sort(key=lambda x: x[0])
    return index


# ---------------------------------------------------------------------------
# Anchors taken from the Planner-only logs
# ---------------------------------------------------------------------------

def load_oro_anchors(ORO_BASE):
    anchors = {}
    dirs = sorted([d for d in os.listdir(ORO_BASE) if d.isdigit()], key=int)
    for rep_str in dirs:
        path = os.path.join(ORO_BASE, rep_str, 'merged_log.xes')
        if not os.path.exists(path):
            continue
        _, _, traces = parse_xes(path)
        all_ts = []
        for t in traces:
            all_ts.extend(get_trace_timestamps(t))
        if all_ts:
            anchors[int(rep_str)] = {
                'start': min(all_ts),
                'span': max(all_ts) - min(all_ts),
            }
    return anchors


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------

def shift_trace(trace, delta):
    tc = deepcopy(trace)
    for ev in [c for c in tc if c.tag.endswith('event')]:
        for attr in ev:
            if attr.get('key') in TS_KEYS:
                try:
                    dt = _parse_ts(attr.get('value', ''))
                    attr.set('value', _fmt_ts(dt + delta))
                except Exception:
                    pass
    return tc


def compress_trace_full(trace, origin, global_min, scale):
    tc = deepcopy(trace)
    for ev in [c for c in tc if c.tag.endswith('event')]:
        for attr in ev:
            if attr.get('key') in TS_KEYS:
                try:
                    dt = _parse_ts(attr.get('value', ''))
                    elapsed = (dt - global_min).total_seconds() * scale
                    attr.set('value', _fmt_ts(origin + timedelta(seconds=elapsed)))
                except Exception:
                    pass
    return tc


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def adapt_window(trace_index, anchor_start, target_span, rng, window_start=None):
    if not trace_index:
        return [], None, 0

    global_min_dt = trace_index[0][0]
    global_max_dt = trace_index[-1][0]
    latest_start  = max(global_min_dt, global_max_dt - target_span)

    if window_start is None:
        range_s = (latest_start - global_min_dt).total_seconds()
        window_start = global_min_dt + timedelta(seconds=rng.uniform(0, max(range_s, 0)))

    window_end = window_start + target_span
    in_window  = [t for (s, t) in trace_index if window_start <= s <= window_end]
    n_found    = len(in_window)

    if n_found >= N_TRACES:
        selected = rng.sample(in_window, N_TRACES)
    elif n_found > 0:
        selected = in_window + rng.choices(in_window, k=N_TRACES - n_found)
    else:
        selected = [t for (_, t) in trace_index[:N_TRACES]]

    delta = anchor_start - window_start
    return [shift_trace(t, delta) for t in selected], window_start, n_found


def adapt_window_systematic(trace_index, anchor_start, target_span,
                             replica_idx, n_replicas, rng):
    global_min_dt = trace_index[0][0]
    global_max_dt = trace_index[-1][0]
    total_s       = (global_max_dt - global_min_dt).total_seconds()
    chunk_s       = total_s / n_replicas
    window_start  = global_min_dt + timedelta(seconds=replica_idx * chunk_s)
    return adapt_window(trace_index, anchor_start, target_span, rng, window_start)


def adapt_resample(real_traces, anchor_start, target_span, rng):
    sampled = rng.choices(real_traces, k=N_TRACES)
    pairs   = sorted(
        [(t, min(ts)) for t in sampled if (ts := get_trace_timestamps(t))],
        key=lambda x: x[1]
    )
    if not pairs:
        return []

    starts     = [p[1] for p in pairs]
    arr_span_s = (starts[-1] - starts[0]).total_seconds()
    tgt_span_s = target_span.total_seconds()

    adapted = []
    for trace, orig_start in pairs:
        if arr_span_s > 0:
            offset_s = (orig_start - starts[0]).total_seconds()
            new_start = anchor_start + timedelta(seconds=offset_s * tgt_span_s / arr_span_s)
        else:
            new_start = anchor_start
        adapted.append(shift_trace(trace, new_start - orig_start))
    return adapted


def adapt_compress(real_traces, anchor_start, target_span, rng):
    sampled = rng.choices(real_traces, k=N_TRACES)
    all_ts  = [ts for t in sampled for ts in get_trace_timestamps(t)]
    if not all_ts:
        return []
    g_min  = min(all_ts)
    g_max  = max(all_ts)
    orig_s = (g_max - g_min).total_seconds()
    scale  = target_span.total_seconds() / orig_s if orig_s > 0 else 1.0
    return [compress_trace_full(t, anchor_start, g_min, scale) for t in sampled]


# ---------------------------------------------------------------------------
# XES output
# ---------------------------------------------------------------------------

def build_xes(original_root, adapted_traces):
    new_root = ET.Element(original_root.tag, original_root.attrib)
    for child in original_root:
        if not child.tag.endswith('trace'):
            new_root.append(deepcopy(child))
    for t in adapted_traces:
        new_root.append(t)
    return ET.ElementTree(new_root)


def save_xes(tree, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ET.indent(tree, space='  ')
    tree.write(path, encoding='unicode', xml_declaration=True)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def trace_stats(traces):
    all_ts = []
    durs   = []
    for t in traces:
        ts = get_trace_timestamps(t)
        if ts:
            all_ts.extend(ts)
            durs.append((max(ts) - min(ts)).total_seconds() / 3600)
    if not all_ts:
        return {}
    return {
        'n_traces': len(traces),
        'n_events': len(all_ts),
        'start': str(min(all_ts)),
        'end': str(max(all_ts)),
        'span_days': round((max(all_ts) - min(all_ts)).total_seconds() / 86400, 2),
        'mean_case_dur_h': round(mean(durs), 2) if durs else 0,
        'median_case_dur_h': round(median(durs), 2) if durs else 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build the adapted real-world log (one reference log per replicate).'
    )
    parser.add_argument('--mode',
                        choices=['window', 'window_systematic', 'resample', 'compress'],
                        default='window_systematic',
                        help="window_systematic is the mode used in the article.")
    parser.add_argument('--replicas', type=int, default=30)
    parser.add_argument('--seed', type=int, default=2021)
    parser.add_argument('--real-log', type=str, default=os.path.join(DATA_DIR, 'logReal.xes'),
                        help='Real-world event log (XES).')
    parser.add_argument('--planner-only-dir', type=str, default=os.path.join(DATA_DIR, 'logOro'),
                        help='Directory with the Planner-only logs <r>/merged_log.xes (anchors).')
    parser.add_argument('--output-dir', type=str, default=os.path.join(DATA_DIR, 'logRealAdaptado'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print('=' * 65)
    print('  generate_adapted_real_log.py')
    print(f'  Mode={args.mode} | Replicates={args.replicas} | Seed={args.seed}')
    print('=' * 65)

    # 1. Cargar logReal
    print('\n[1/4] Loading the real-world log ...')
    _, real_root, real_traces = parse_xes(args.real_log)
    trace_index = build_trace_index(real_traces)
    real_dates  = [t[0] for t in trace_index]
    print(f'      {len(real_traces)} traces | '
          f'{min(real_dates).date()} -> {max(real_dates).date()} '
          f'({(max(real_dates)-min(real_dates)).days} days)')

    # 2. Anclas de logOro
    print('\n[2/4] Loading the anchors of the Planner-only logs ...')
    oro_anchors = load_oro_anchors(args.planner_only_dir)
    spans       = [v['span'].total_seconds() / 86400 for v in oro_anchors.values()]
    print(f'      {len(oro_anchors)} replicates | span: min={min(spans):.1f}d '
          f'max={max(spans):.1f}d mean={mean(spans):.1f}d')
    default_anchor = list(oro_anchors.values())[0]['start']
    default_span   = timedelta(days=mean(spans))

    # 3. Generar
    print(f'\n[3/4] Generating {args.replicas} replicates ...')
    rng  = random.Random(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)
    rows = []
    skip = []

    for rep in range(1, args.replicas + 1):
        info         = oro_anchors.get(rep, {})
        anchor_start = info.get('start', default_anchor)
        target_span  = info.get('span', default_span)

        try:
            w_start = None
            n_found = None

            if args.mode == 'window':
                adapted, w_start, n_found = adapt_window(
                    trace_index, anchor_start, target_span, rng)
            elif args.mode == 'window_systematic':
                adapted, w_start, n_found = adapt_window_systematic(
                    trace_index, anchor_start, target_span, rep - 1, args.replicas, rng)
            elif args.mode == 'resample':
                adapted = adapt_resample(real_traces, anchor_start, target_span, rng)
            else:
                adapted = adapt_compress(real_traces, anchor_start, target_span, rng)

            if not adapted:
                print(f'  [WARN] Replicate {rep:2d}: no traces - skipped')
                skip.append(rep)
                continue

            st = trace_stats(adapted)

            if not args.dry_run:
                t = build_xes(real_root, adapted)
                save_xes(t, os.path.join(args.output_dir, str(rep), 'merged_log.xes'))

            rows.append({
                'replica': rep, 'mode': args.mode,
                'n_traces': st.get('n_traces', 0),
                'n_events': st.get('n_events', 0),
                'start': st.get('start', ''),
                'end': st.get('end', ''),
                'span_days': st.get('span_days', 0),
                'mean_case_dur_h': st.get('mean_case_dur_h', 0),
                'median_case_dur_h': st.get('median_case_dur_h', 0),
                'oro_anchor_start': str(anchor_start),
                'oro_target_span_days': round(target_span.total_seconds() / 86400, 2),
                'window_start_in_real': str(w_start)[:19] if w_start else '',
                'n_found_in_window': n_found if n_found is not None else '',
            })

            extra = (f' | real_window={str(w_start)[:10]}, {n_found} cases'
                     if w_start else '')
            print(f'  Replicate {rep:2d}: {st["n_traces"]} traces | '
                  f'{st["start"][:10]} -> {st["end"][:10]} '
                  f'({st["span_days"]:.1f}d){extra}')

        except Exception as e:
            import traceback
            print(f'  [ERROR] Replicate {rep:2d}: {e}')
            traceback.print_exc()
            skip.append(rep)

    # 4. Reporte
    print('\n[4/4] Writing the report ...')
    if rows and not args.dry_run:
        rp = os.path.join(args.output_dir, 'generation_report.csv')
        with open(rp, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f'      -> {rp}')

    print('\n' + '=' * 65)
    print('  SUMMARY')
    print(f'  Generated : {len(rows)} | Skipped: {len(skip)} {skip if skip else ""}')
    if rows:
        final_spans = [r['span_days'] for r in rows]
        final_durs  = [r['mean_case_dur_h'] for r in rows]
        print(f'  Span (d)  : mean={mean(final_spans):.1f} '
              f'min={min(final_spans):.1f} max={max(final_spans):.1f}')
        print(f'  Case dur.(h): mean={mean(final_durs):.1f} '
              f'min={min(final_durs):.1f} max={max(final_durs):.1f}')
        print(f'  Target (Planner-only) span (d): mean={mean(spans):.1f}')
    if not args.dry_run:
        print(f'  Directory: {args.output_dir}')
    print('=' * 65)


if __name__ == '__main__':
    main()

