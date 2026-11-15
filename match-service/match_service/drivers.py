"""Who plays a clone in the real game, and whether a clone can be played with the current setup.

Two drivers exist today (chosen for the whole service by CS2_BOTS):
  stand_in        the built-in CS2-Bot-Improver bot named in the profile's `stand_in_bot`.
  clone_director  Arjun's CloneDirector plugin, which plays the clone's route files for its side and
                  then hands over to the bot base's own fighting logic.

Learned models do not need a driver of their own. A trained identity model produces route files
(source "generated", SPEC.md section 8.5) that CloneDirector plays like recorded ones. To use them:
fill the clone profile's `model` field, put the generated segments in the clone's folder, and start
the service with CS2_CLONE_ROUTES=generated. Nothing here, in the API or in the demo pages has to
change. A clone whose identity test failed keeps `model: null` and plays recorded routes.
"""

from .core import Settings
from .models import Clone, CloneInfo

STAND_IN = "stand_in"
CLONE_DIRECTOR = "clone_director"


def describe(clone: Clone, settings: Settings) -> CloneInfo:
    """How this clone would be played now, and whether it can be."""
    base = clone.model_dump()
    shared = (f"; shares installed bot {clone.stand_in_bot} with {clone.clone_id[:-1]}_v1, one per match"
              if clone.stand_in_bot and clone.clone_id.endswith("L") else "")
    if settings.backend != "cs2":
        return CloneInfo(**base, driver="mock", label="simulated", playable=True)
    if settings.cs2_bots == "clone":
        generated = settings.cs2_routes == "generated"
        label = ("CloneDirector, generated routes" if generated else "CloneDirector, recorded routes")
        # A profile can name a model whose paths are not yet route files (donkLF, brokyLF): it still
        # plays recorded routes, and generated mode has nothing to play for it.
        pending = isinstance(clone.model, dict) and clone.model.get("routes_generated") is False
        if pending and generated:
            return CloneInfo(**base, driver=CLONE_DIRECTOR, label=label, playable=False,
                             reason="model named, but no generated routes exist for it yet")
        if pending:
            label += " (model adapter not converted to routes yet)"
        if generated and not clone.model:
            return CloneInfo(**base, driver=CLONE_DIRECTOR, label=label + shared, playable=False,
                             reason="no model in the profile, so no generated routes")
        return CloneInfo(**base, driver=CLONE_DIRECTOR, label=label + shared, playable=True)
    if not clone.stand_in_bot:
        return CloneInfo(**base, driver=STAND_IN, label="stand-in bot", playable=False,
                         reason="no stand-in bot in the profile")
    return CloneInfo(**base, driver=STAND_IN, label=f"stand-in bot ({clone.stand_in_bot})" + shared, playable=True)
