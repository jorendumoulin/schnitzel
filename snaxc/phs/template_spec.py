from __future__ import annotations

import itertools
from collections.abc import Iterable

from xdsl.dialects.builtin import AffineMapAttr, ArrayAttr, DenseArrayBase
from xdsl.ir.affine import AffineDimExpr, AffineMap

from snaxc.dialects import phs
from snaxc.ir.dart.access_pattern import Template, TemplatePattern


def _union_map_at_position(maps_at_position: list[AffineMap], num_dims: int) -> AffineMap | None:
    """Build a union AffineMap over ``num_dims`` whose results are the
    distinct dim positions referenced by any mode's map at this operand
    position, sorted by dim index. Used to decide port shape and per-PE
    wiring when multiple modes share the same accelerator: the wider mode
    dictates the port shape, narrower modes broadcast their unused dims at
    runtime via the per-mode streamer mask.

    Returns ``None`` if any mode's result expression is not a pure
    ``AffineDimExpr`` (we don't try to union complex expressions today).
    """
    used_dims: set[int] = set()
    for m in maps_at_position:
        if m.num_dims != num_dims:
            continue  # mode's map doesn't match template bounds — dart handles tiling
        for result in m.results:
            if isinstance(result, AffineDimExpr):
                used_dims.add(result.position)
            else:
                return None
    sorted_dims = sorted(used_dims)
    return AffineMap(num_dims, 0, tuple(AffineDimExpr(d) for d in sorted_dims))


PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"
INDEXING_MAPS_ATTR_NAME = "phs.indexing_maps"


class TemplateSpec:
    """
    Description of one PE's input/output access pattern over the spatial PE-array bounds.

    Convention (set by the encode pass + adjusted by the prune-unused-carries
    pass): the trailing ``len(paired_outputs)`` entries of ``input_maps`` are
    carry-input sides of readWrite streamers, paired by position with the
    outputs whose indices are listed in ``paired_outputs`` — specifically,
    carry-input ``k`` (at PE-input index ``num_pure_inputs + k``) feeds back
    into output ``paired_outputs[k]``. Outputs whose index is NOT in
    ``paired_outputs`` are pure write-only streamers. ``paired_outputs``
    defaults to ``range(len(output_maps))`` (every output paired, in order)
    for back-compat with callers that don't go through the encode pass.
    """

    input_maps: tuple[AffineMap, ...]
    output_maps: tuple[AffineMap, ...]
    template_bounds: tuple[int, ...]
    paired_outputs: tuple[int, ...]
    # Per-mode maps. Each entry is one mode's (input_maps, output_maps) tuple
    # in that mode's original linalg operand order (ins... then outs...).
    # A mode's inner list may be SHORTER than the canonical widened counts —
    # a missing slot means the mode does not use that input/output (dead slot
    # inserted by ``align_schemas`` during merge). Downstream mask emission
    # treats dead slots as "no dim accessed" in that mode.
    per_mode_input_maps: tuple[tuple[AffineMap, ...], ...]
    per_mode_output_maps: tuple[tuple[AffineMap, ...], ...]

    def __init__(
        self,
        input_maps: tuple[AffineMap, ...],
        output_maps: tuple[AffineMap, ...],
        template_bounds: tuple[int, ...],
        paired_outputs: tuple[int, ...] | None = None,
        per_mode_input_maps: tuple[tuple[AffineMap, ...], ...] | None = None,
        per_mode_output_maps: tuple[tuple[AffineMap, ...], ...] | None = None,
    ):
        self.input_maps = input_maps
        self.output_maps = output_maps
        self.template_bounds = template_bounds
        self.paired_outputs = tuple(range(len(output_maps))) if paired_outputs is None else tuple(paired_outputs)
        # Default per-mode lists: one mode matching the canonical flat view.
        self.per_mode_input_maps = (input_maps,) if per_mode_input_maps is None else per_mode_input_maps
        self.per_mode_output_maps = (output_maps,) if per_mode_output_maps is None else per_mode_output_maps
        assert len(self.per_mode_input_maps) == len(self.per_mode_output_maps), (
            "per_mode_input_maps and per_mode_output_maps must have the same number of modes"
        )
        assert len(self.input_maps) > 0, "Expect input_maps to be non-empty"
        assert len(self.output_maps) > 0, "Expect output_maps to be non-empty"
        assert all(0 <= k < len(output_maps) for k in self.paired_outputs), (
            f"paired_outputs indices {self.paired_outputs} out of range [0, {len(output_maps)})"
        )
        assert len(set(self.paired_outputs)) == len(self.paired_outputs), (
            f"paired_outputs has duplicates: {self.paired_outputs}"
        )
        assert len(self.input_maps) >= len(self.paired_outputs), (
            "Each paired output must have a matching carry block-arg — "
            f"got {len(self.input_maps)} inputs and {len(self.paired_outputs)} paired outputs"
        )
        assert self._no_symbols(), "No symbols expected in any affine map of template_spec"
        assert self._same_dims(), "Expect all AffineMaps to have equal number of dims"
        assert len(template_bounds) == self.input_maps[0].num_dims, "Expect number of iterators and bounds to be equal"

    @property
    def num_outputs(self) -> int:
        return len(self.output_maps)

    @property
    def carry_no(self) -> int:
        return len(self.paired_outputs)

    @property
    def num_pure_inputs(self) -> int:
        return len(self.input_maps) - self.carry_no

    @property
    def readwrite_pairs(self) -> dict[int, int]:
        """
        PE-input index -> PE-output index for each readWrite pair. Carry ``k``
        (at PE-input ``num_pure_inputs + k``) pairs with output ``paired_outputs[k]``.
        """
        return {self.num_pure_inputs + k: self.paired_outputs[k] for k in range(self.carry_no)}

    def __str__(self) -> str:
        _str: str = ""
        _str += "maps:\n"
        for i, i_map in enumerate(self.input_maps):
            _str += f"i{i} : {i_map}\n"
        for o, o_map in enumerate(self.output_maps):
            _str += f"o{o} : {o_map}\n"

        _str += "bounds:\n"
        for b, bound in enumerate(self.template_bounds):
            _str += f"d{b} : {bound}\n"
        return _str

    def _no_symbols(self) -> bool:
        comparison = [map.num_symbols == 0 for map in self.input_maps + self.output_maps]
        return all(comparison)

    def _same_dims(self) -> bool:
        first_num_dims = self.input_maps[0].num_dims
        comparison = [map.num_dims == first_num_dims for map in (self.input_maps + self.output_maps)[:1]]
        return all(comparison)

    def _get_sizes(self, maps: tuple[AffineMap, ...]) -> list[tuple[int, ...]]:
        return [map.eval(self.template_bounds, ()) for map in maps]

    def get_input_sizes(self) -> list[tuple[int, ...]]:
        return self._get_sizes(self.input_maps)

    def get_output_sizes(self) -> list[tuple[int, ...]]:
        return self._get_sizes(self.output_maps)

    def get_iterations(self) -> Iterable[tuple[int, ...]]:
        return itertools.product(*[range(bound) for bound in self.template_bounds])

    def get_dart_template(self) -> Template:
        # The carry-input of each readWrite pair shares its streamer (and its
        # access pattern) with the matching output, so the dart-side template
        # only describes one logical operand per pair: pure read inputs first,
        # then outputs. This matches the operand count of the dart op produced
        # from the original linalg (len(ins) + len(outs)).
        template = [*self.input_maps[: self.num_pure_inputs], *self.output_maps]
        template_bounds = self.template_bounds
        return Template(TemplatePattern(template_bounds, tp) for tp in template)

    @staticmethod
    def derive_template_spec(pe: phs.PEOp, bounds: tuple[int, ...]) -> TemplateSpec:
        """Derive a TemplateSpec from a PEOp and array bounds.

        Uses the propagated linalg ``phs.indexing_maps`` attribute when it
        matches the template's dim count — preserving scalar/reduced maps that
        signal spatial-chain reductions. Falls back to identity maps in either
        of two cases:
          * the attribute is absent (legacy tests that build a PEOp directly);
          * the linalg map's dim count doesn't match ``len(bounds)`` (the dart
            scheduler handles the tile split elsewhere, and the template's
            in-cycle access pattern is still identity under the remaining
            spatial dim).
        """
        num_data = len(pe.data_operands())
        num_outputs = len(pe.get_terminator().operands)
        num_dims = len(bounds)
        # paired_outputs comes from the encode pass (initial = all outputs) and
        # may have been shrunk by the prune-unused-carries pass.
        paired_attr = pe.attributes.get(PAIRED_OUTPUTS_ATTR_NAME)
        if paired_attr is None:
            # Legacy fallback for tests that build a PEOp directly without
            # going through the encode pass: assume every output is paired.
            paired_outputs = tuple(range(min(num_outputs, num_data)))
        else:
            assert isinstance(paired_attr, DenseArrayBase)
            paired_outputs = tuple(int(v) for v in paired_attr.get_values())

        # Pull the linalg operand maps. Stored as
        # ``ArrayAttr[ArrayAttr[AffineMapAttr]]`` by the encode pass — the
        # outer list is indexed by mode, each inner list has one AffineMap
        # per linalg operand in the order [ins..., outs...]. A mode's inner
        # list reflects that mode's original linalg shape; slots beyond it
        # in the widened PE are "dead" for that mode.
        indexing_attr = pe.attributes.get(INDEXING_MAPS_ATTR_NAME)
        per_mode_maps: tuple[tuple[AffineMap, ...], ...] = ()
        if indexing_attr is not None and isinstance(indexing_attr, ArrayAttr):
            modes: list[tuple[AffineMap, ...]] = []
            for mode_attr in indexing_attr.data:
                if isinstance(mode_attr, ArrayAttr):
                    modes.append(tuple(m.data for m in mode_attr.data if isinstance(m, AffineMapAttr)))
                elif isinstance(mode_attr, AffineMapAttr):
                    # Legacy flat attribute — treat as a single mode.
                    modes = [tuple(m.data for m in indexing_attr.data if isinstance(m, AffineMapAttr))]
                    break
            per_mode_maps = tuple(modes)

        # Build the canonical flat ``input_maps`` / ``output_maps`` view used
        # for port shape and per-PE wiring.
        #
        # PURE inputs: per operand position we take the *union* across modes
        # of the dim positions any mode's map result expression references —
        # i.e., the wider-mode shape wins. Narrower modes broadcast their
        # unused dims at runtime via the per-mode streamer mask emitted by
        # ``build_pe_array_body``. This lets a matmul mode with broadcast
        # inputs share an accelerator with a wider elementwise mode that uses
        # all dims, without needing per-mode block-arg adapters.
        #
        # CARRY inputs and OUTPUTS: we DON'T union — they're tied to the
        # output's reduction structure. Unioning the output would erase
        # reduction info (matmul's (d0,d1,d2)->(d0,d1) unioned with a 3D
        # identity becomes identity, losing the K-chain), and unioning the
        # carry would put it out of sync with the output port shape and break
        # chain init wiring. Instead we pick the first eligible mode's
        # carry/output maps as canonical. Modes that disagree on
        # carry/output shape are out of scope for this merge path and need a
        # more invasive design (per-mode output assembly).
        #
        # Only modes whose map ``num_dims`` matches ``num_dims`` contribute;
        # modes with mismatched dim counts are split off to temporal loops by
        # the dart scheduler and don't constrain the in-cycle shape. The
        # union helper requires result expressions to be pure
        # ``AffineDimExpr`` — if any mode uses a complex expression we fall
        # back to picking a single same-num_dims mode as canonical (prior
        # behaviour) and finally to identity maps.
        eligible_modes = [
            mode
            for mode in per_mode_maps
            if len(mode) == num_data and len(mode) >= num_outputs and all(m.num_dims == num_dims for m in mode)
        ]
        num_pure_inputs = num_data - num_outputs

        if eligible_modes:
            canonical = eligible_modes[0]
            # Try union for pure inputs only; on any complex result expr fall
            # back to canonical for that slot.
            input_maps_list: list[AffineMap] = []
            for i in range(num_pure_inputs):
                u = _union_map_at_position([mode[i] for mode in eligible_modes], num_dims)
                input_maps_list.append(u if u is not None else canonical[i])
            # Carries: canonical's view (the encode-pass convention pairs
            # them with outputs by position; mixing modes' carry maps would
            # break that).
            input_maps_list.extend(canonical[num_pure_inputs:])
            input_maps = tuple(input_maps_list)
            output_maps = canonical[num_pure_inputs:]
        else:
            input_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_data))
            output_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_outputs))

        # Split per-mode maps into input- and output-sides. Each mode's raw
        # list is ``[ins..., outs...]``; the trailing ``num_outputs`` entries
        # are the outputs. If a mode's list is shorter than ``num_outputs``
        # (shouldn't happen for encoded PEs) we keep the mode empty on that
        # side — the consumer should treat missing slots as dead.
        per_mode_input: list[tuple[AffineMap, ...]] = []
        per_mode_output: list[tuple[AffineMap, ...]] = []
        for mode in per_mode_maps:
            if len(mode) >= num_outputs:
                per_mode_input.append(mode[: len(mode) - num_outputs])
                per_mode_output.append(mode[len(mode) - num_outputs :])
            else:
                per_mode_input.append(mode)
                per_mode_output.append(())
        if not per_mode_input:
            # No per-mode info recorded (legacy tests). Treat as a single
            # mode using the canonical view.
            per_mode_input = [input_maps[: num_data - num_outputs]]
            per_mode_output = [output_maps]

        return TemplateSpec(
            input_maps=input_maps,
            output_maps=output_maps,
            template_bounds=bounds,
            paired_outputs=paired_outputs,
            per_mode_input_maps=tuple(per_mode_input),
            per_mode_output_maps=tuple(per_mode_output),
        )
