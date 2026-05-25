import pytest
from xdsl.ir import Block, Region, VerifyException

from snaxc.dialects.snax_stream import StreamingRegionOp, StridePattern


def test_canonicalize_stride_pattern():
    # bounds of 1 are removed
    s = StridePattern([2, 1, 1], [0, 0, 0], [1])
    s = s.canonicalize()
    assert s == StridePattern([2], [0], [1])

    s = StridePattern([1, 1, 1], [0, 0, 0], [1]).canonicalize()
    assert s == StridePattern([], [], [1])

    # zeros are kept to correctly disable streamers
    s = StridePattern([0, 0, 0], [0, 0, 0], [1]).canonicalize()
    assert s == StridePattern([0, 0, 0], [0, 0, 0], [1])

    # if possible, wrap
    s = StridePattern([4, 4, 4], [1, 4, 16], [1]).canonicalize()
    assert s == StridePattern([4 * 4 * 4], [1], [1])


def _make_region(patterns: list[StridePattern]) -> StreamingRegionOp:
    return StreamingRegionOp(
        inputs=[],
        outputs=[],
        stride_patterns=patterns,
        dynamic_operands=[],
        accelerator="dummy",
        body=Region(Block()),
    )


def test_streaming_region_mismatched_cycles_rejected():
    # Streamer 0 runs 1 cycle, streamer 1 runs 2 cycles, streamer 2 runs 1 cycle.
    # This is the matmul-kernel failure mode: hardware would stall waiting on the
    # longest streamer, so reject at compile time.
    op = _make_region(
        [
            StridePattern([1, 1], [0, 0], [1]),
            StridePattern([1, 2], [0, 0], [1]),
            StridePattern([1, 1], [0, 0], [1]),
        ]
    )
    with pytest.raises(VerifyException, match="same number of cycles"):
        op.verify()


def test_streaming_region_matched_cycles_accepted():
    op = _make_region(
        [
            StridePattern([2, 2], [0, 0], [1]),
            StridePattern([4], [0], [1]),
            StridePattern([1, 4], [0, 0], [1]),
        ]
    )
    op.verify()


def test_streaming_region_disabled_streamer_ignored():
    # A streamer with any zero upper bound is disabled (canonical "off" encoding)
    # and must not participate in the cycle-count comparison.
    op = _make_region(
        [
            StridePattern([2, 2], [0, 0], [1]),
            StridePattern([0, 0], [0, 0], [1]),
            StridePattern([4], [0], [1]),
        ]
    )
    op.verify()
