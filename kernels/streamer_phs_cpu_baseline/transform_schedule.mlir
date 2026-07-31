// No-op transform schedule. Nothing is annotated with `phs_acc`, so no
// accelerator is generated and the kernel falls through to the core.
module @transforms attributes { transform.with_named_sequence } {
  transform.named_sequence @__transform_main(
      %root: !transform.any_op {transform.readonly}) {
    transform.yield
  }
}
