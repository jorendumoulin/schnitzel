from __future__ import annotations

import itertools
from collections.abc import Iterable

from xdsl.dialects.builtin import IntegerAttr
from xdsl.ir.affine import AffineMap

from snaxc.dialects import phs
from snaxc.ir.dart.access_pattern import Template, TemplatePattern

CARRY_NO_ATTR_NAME = "phs.carry_no"


class TemplateSpec:
    """
    Description of one PE's input/output access pattern over the spatial PE-array bounds.

    Convention (set by the encode pass + adjusted by the prune-unused-carries
    pass): the trailing ``carry_no`` entries of ``input_maps`` are carry-input
    sides of readWrite streamers, paired by position with the leading
    ``carry_no`` entries of ``output_maps``. Outputs after the first
    ``carry_no`` are pure write-only streamers. ``carry_no`` defaults to
    ``len(output_maps)`` (every output paired) for back-compat with callers
    that don't go through the encode pass.
    """

    input_maps: tuple[AffineMap, ...]
    output_maps: tuple[AffineMap, ...]
    template_bounds: tuple[int, ...]
    carry_no: int

    def __init__(
        self,
        input_maps: tuple[AffineMap, ...],
        output_maps: tuple[AffineMap, ...],
        template_bounds: tuple[int, ...],
        carry_no: int | None = None,
    ):
        self.input_maps = input_maps
        self.output_maps = output_maps
        self.template_bounds = template_bounds
        self.carry_no = len(output_maps) if carry_no is None else carry_no
        assert len(self.input_maps) > 0, "Expect input_maps to be non-empty"
        assert len(self.output_maps) > 0, "Expect output_maps to be non-empty"
        assert 0 <= self.carry_no <= len(self.output_maps), (
            f"carry_no={self.carry_no} must be in [0, {len(self.output_maps)}]"
        )
        assert len(self.input_maps) >= self.carry_no, (
            "Each carry input must have a matching block-arg — "
            f"got {len(self.input_maps)} inputs and carry_no={self.carry_no}"
        )
        assert self._no_symbols(), "No symbols expected in any affine map of template_spec"
        assert self._same_dims(), "Expect all AffineMaps to have equal number of dims"
        assert len(template_bounds) == self.input_maps[0].num_dims, "Expect number of iterators and bounds to be equal"

    @property
    def num_outputs(self) -> int:
        return len(self.output_maps)

    @property
    def num_pure_inputs(self) -> int:
        return len(self.input_maps) - self.carry_no

    @property
    def readwrite_pairs(self) -> dict[int, int]:
        """
        Positional pairing of PE inputs to PE outputs: the trailing ``carry_no``
        inputs pair with the leading ``carry_no`` outputs as readWrite streamers.
        """
        return {self.num_pure_inputs + k: k for k in range(self.carry_no)}

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
        """Derive a TemplateSpec from a PEOp and array bounds using identity maps."""
        num_data = len(pe.data_operands())
        num_outputs = len(pe.get_terminator().operands)
        num_dims = len(bounds)
        # carry_no comes from the encode pass (= initial number of linalg outs)
        # and may have been lowered by the prune-unused-carries pass.
        carry_attr = pe.attributes.get(CARRY_NO_ATTR_NAME)
        if carry_attr is None:
            # Legacy fallback for tests that build a PEOp directly without going
            # through the encode pass: assume every output is paired (= today's
            # default after encode).
            carry_no = min(num_outputs, num_data)
        else:
            assert isinstance(carry_attr, IntegerAttr)
            carry_no = carry_attr.value.data
        input_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_data))
        output_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_outputs))
        return TemplateSpec(
            input_maps=input_maps,
            output_maps=output_maps,
            template_bounds=bounds,
            carry_no=carry_no,
        )
