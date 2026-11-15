"""Independent edge checks; strict xfails document confirmed defects, not fixes."""
import asyncio
import json
import math
import sys
from pathlib import Path

import brotli
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'match-service'))
from match_service.core import Settings, MatchRecord, now
from match_service.main import create_app
from match_service.models import Match
from match_service.replay import RouteLibrary, Trace, gsi_players
from match_service.backends.mock import MockBackend


def library(tmp_path, content=None, missing=False):
    profile = {'clone_id':'sample', 'routes': {'T':[{'recording':'sample_t', 'file':'sample/route.json.br'}]}}
    (tmp_path/'sample.json').write_text(json.dumps(profile))
    if not missing:
        (tmp_path/'sample').mkdir()
        (tmp_path/'sample/route.json.br').write_bytes(content if content is not None else brotli.compress(b'{"Ticks":[]}'))
    return RouteLibrary(tmp_path)


def test_all_committed_routes_are_finite_monotonic_8hz_and_same_side():
    lib = RouteLibrary(ROOT/'clones')
    n = 0
    for cid in lib.clone_ids():
        for meta in lib.routes(cid):
            route = lib.route(cid, meta['recording'])
            assert route['side'] == meta['side']
            assert len(route['path']) > 1
            for i, point in enumerate(route['path']):
                assert all(math.isfinite(v) for v in point)
                assert point[0] == i / 8
            n += 1
    assert n == 159


def test_invalid_ids_and_nonexistent_match():
    with TestClient(create_app(Settings(backend='mock'))) as c:
        for url in ['/matches/nonexistent', '/matches/nonexistent/trace', '/matches/nonexistent/compare?round=1&player=donk', '/replay/clones/not_real', '/replay/clones/donk_v1/routes/not_real']:
            assert c.get(url).status_code == 404
        assert c.post('/matches/nonexistent/stop').status_code == 404


@pytest.mark.xfail(strict=True, reason='QA-1: closest crashes when a listed route file is missing')
def test_missing_route_is_skipped_by_closest(tmp_path):
    lib = library(tmp_path, missing=True)
    assert lib.closest('sample', 'T', [[0,0,0],[1,1,1],[2,2,2]]) is None


@pytest.mark.xfail(strict=True, reason='QA-1: closest divides/mins empty recording paths')
def test_empty_route_is_skipped_by_closest(tmp_path):
    assert library(tmp_path).closest('sample', 'T', [[0,0,0],[1,1,1],[2,2,2]]) is None


@pytest.mark.xfail(strict=True, reason='QA-1: malformed Brotli route escapes as an exception')
def test_corrupt_route_is_unavailable_instead_of_crashing(tmp_path):
    assert library(tmp_path, content=b'bad').route('sample','sample_t') is None


@pytest.mark.xfail(strict=True, reason='QA-2: trace admits NaN and Infinity from GSI')
def test_nonfinite_gsi_positions_are_rejected():
    assert gsi_players({'allplayers':{'a':{'position':'nan, inf, 0'}}}) == []


@pytest.mark.xfail(strict=True, reason='QA-2: trace retains nonfinite coordinates')
def test_nonfinite_trace_points_are_rejected():
    t = Trace('sample','de_mirage','gsi')
    t.add(1,0,'a','T',float('nan'),0)
    assert t.to_json()['rounds'] == []


def test_duplicate_and_out_of_order_trace_samples_do_not_reverse_time():
    t = Trace('sample','de_mirage','gsi')
    for seconds in [0, 0, .125, .1, .25]:
        t.add(1,seconds,'a','T',seconds,0)
    assert [p[0] for p in t.to_json()['rounds'][0]['players'][0]['path']] == [0,.12,.25]


@pytest.mark.xfail(strict=True, reason='QA-3: alive updates resume a dead player path')
def test_death_is_terminal_in_one_round():
    t = Trace('sample','de_mirage','gsi')
    t.add(1,0,'a','T',0,0)
    t.add(1,1,'a','T',1,0,alive=False)
    t.add(1,2,'a','T',2,0)
    player = t.to_json()['rounds'][0]['players'][0]
    assert player['died_at'] == 1
    assert player['path'] == [[0,0,0]]


@pytest.mark.xfail(strict=True, reason='QA-4: mock stop leaves live_round set and trace unsaved')
def test_stopped_mock_trace_is_finalized_and_saved(tmp_path):
    async def run():
        async def emit(*args): pass
        backend = MockBackend(Settings(trace_dir=tmp_path),emit)
        record = MatchRecord(Match(match_id='sample', status='live',map='de_mirage',mode='wingman',players=[],created_at=now()),None,False)
        record.trace = Trace('sample','de_mirage','simulated')
        record.trace.add(1,0,'a','T',0,0)
        record.trace.live_round=1
        await backend.stop(record)
        assert record.trace.live_round is None
        assert (tmp_path/'sample.json').is_file()
    asyncio.run(run())


@pytest.mark.xfail(strict=True, reason='QA-5: mock announces recording URL despite never recording')
def test_finished_mock_has_no_downloadable_demo_url(tmp_path):
    async def run():
        async def emit(*args): pass
        backend = MockBackend(Settings(start_seconds=0,warmup_seconds=0,round_seconds=0),emit,RouteLibrary(tmp_path))
        record = MatchRecord(Match(match_id='sample', status='starting',map='de_mirage',mode='wingman',players=[],created_at=now()),None,False)
        backend.start(record,{})
        await record.task
        assert record.match.demo_url is None
    asyncio.run(run())
