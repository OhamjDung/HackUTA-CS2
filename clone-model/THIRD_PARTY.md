# Training starting points

- CS-NET v4, Gary2005 and contributors, MIT. Pinned revision:
  `268dd2193c8a3d6e330c07dde5a851196c94eeaa`,
  <https://github.com/Gary2005/cs-net>.
  The parser, replay filters, inventory mapping, wall raycasts, round features, window builder,
  shuffler, model, tokenizer, and free-running prediction engine are used directly from that
  checkout. NPZ caches preserve the upstream round arrays; packaging replaces WDS, not features.
  The trainer restricts decoder work to each target player's last input tick and trains only
  the added adapter. It never updates the pretrained backbone. See `third_party/CSNET_LICENSE`.
  `map_review.py` copies, in reduced form, the Open3D mesh loading and ray casting of
  `scripts/training_data/map_loader.py` and the coordinate scale, axis mapping and 64-unit eye
  height of `scripts/training_data/config.py`; its path checks are new.
- CS2 Clone Lab, Hudson Pagni, MIT. Pinned revision:
  `2d3f50eeab9d6883abdb58d83f8c9bd1538b194a`,
  <https://github.com/hpagni/cs2-clone-lab>.
  `identity.py` adapts `sim/identity.py`'s dense Steam-ID registry, padding identity, and
  zero-initialized FiLM. A new explicit unknown-ID gate prevents a trained shared bias from
  changing the baseline, and a hook applies identities to upstream inference.
  See `third_party/CLONE_LAB_LICENSE`.
- Julien Blanchon / OpenCS2, CC BY 4.0, provides the ten source match recordings. The tournament
  recordings remain subject to their organizers' terms. Raw demos, features, and weights are
  outside Git. Public dataset: <https://huggingface.co/datasets/blanchon/opencs2_dataset_demo>.

The glue for match splits, identity alignment, target-only training, checkpoint selection, and
identity-swap reporting is new. Upstream implementations do not provide this project's complete
donk/broky fine-tuning run. Training does not establish professional skill or identical quirks.
