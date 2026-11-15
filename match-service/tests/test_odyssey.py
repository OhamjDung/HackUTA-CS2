"""Mode checks prevent advertising an immortal stand-in without the damage plugin."""
import json
from pathlib import Path
import pytest
from match_service.core import Settings
from match_service.drivers import describe
from match_service.models import Clone


@pytest.mark.parametrize('name', ['poseidon', 'odysseus', 'menelaus', 'telemachus', 'melantho'])
def test_odyssey_requires_director_and_never_claims_generated_routes(name):
    profile = json.loads((Path(__file__).resolve().parents[2] / 'clones' / (name+'.json')).read_text())
    clone = Clone.model_validate(profile)
    def config(**kw): return Settings(backend='cs2', **kw)
    standin = describe(clone, config(cs2_bots='stand_in'))
    assert not standin.playable and 'CloneDirector' in standin.reason
    generated = describe(clone, config(cs2_bots='clone', cs2_routes='generated'))
    assert not generated.playable and 'authored' in generated.reason
    native = describe(clone, config(cs2_bots='clone', cs2_routes='recorded'))
    assert native.playable and 'authored native AI' in native.label
    assert describe(clone, Settings(backend='mock')).label == 'simulated'
