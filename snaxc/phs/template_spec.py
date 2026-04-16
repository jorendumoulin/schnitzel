from __future__ import annotations

import itertools
from collections.abc import Iterable

from xdsl.ir.affine import AffineMap

from snaxc.dialects import phs
from snaxc.ir.dart.access_pattern import Template, TemplatePattern


class TemplateSpec:
    """
    Description of one PE's input/output access pattern over the spatial PE-array bounds.

    Convention (set by the encode pass): every linalg `outs` operand becomes a
    PE data-input AND a PE output, paired by position. The trailing
    ``len(output_maps)`` entries of ``input_maps`` are the carry-in side of those
    pairs and share a logical (readWrite) streamer with the corresponding
    output. ``input_maps`` therefore has ``num_pure_inputs + len(output_maps)``
    entries; the carry-in maps coincide by construction with the matching output
    maps.
    """

    input_maps: tuple[AffineMap, ...]
    output_maps: tuple[AffineMap, ...]
    template_bounds: tuple[int, ...]

    def __init__(
        self, input_maps: tuple[AffineMap, ...], output_maps: tuple[AffineMap, ...], template_bounds: tuple[int, ...]
    ):
        self.input_maps = input_maps
        self.output_maps = output_maps
        self.template_bounds = template_bounds
        assert len(self.input_maps) > 0, "Expect input_maps to be non-empty"
        assert len(self.output_maps) > 0, "Expect output_maps to be non-empty"
        assert len(self.input_maps) >= len(self.output_maps), (
            "Each output must be paired with a carry input — "
            f"got {len(self.input_maps)} inputs and {len(self.output_maps)} outputs"
        )
        assert self._no_symbols(), "No symbols expected in any affine map of template_spec"
        assert self._same_dims(), "Expect all AffineMaps to have equal number of dims"
        assert len(template_bounds) == self.input_maps[0].num_dims, "Expect number of iterators and bounds to be equal"

    @property
    def num_outputs(self) -> int:
        return len(self.output_maps)

    @property
    def num_pure_inputs(self) -> int:
        return len(self.input_maps) - self.num_outputs

    @property
    def readwrite_pairs(self) -> dict[int, int]:
        """
        Positional pairing of PE inputs to PE outputs, derived from the encode-pass
        convention (last K data inputs are carries paired with the K outputs).
        """
        return {self.num_pure_inputs + k: k for k in range(self.num_outputs)}

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
        input_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_data))
        output_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_outputs))
        return TemplateSpec(input_maps=input_maps, output_maps=output_maps, template_bounds=bounds)
