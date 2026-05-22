// No-op transform schedule. The PHS accelerator assignment (phs_acc) and
// per-PE array bounds (phs_array_bounds) are declared directly on the
// linalg.generic op in bias.mlir.
module @transforms attributes { transform.with_named_sequence } {
  transform.named_sequence @__transform_main(
      %root: !transform.any_op {transform.readonly}) {
    transform.yield
  }
}
