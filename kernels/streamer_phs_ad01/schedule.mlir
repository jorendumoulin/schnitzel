module @transforms attributes { transform.with_named_sequence } {
  transform.named_sequence @__transform_main(
      %root: !transform.any_op {transform.readonly}) {
    %matmul = transform.collect_matching @match_generic in %root
      : (!transform.any_op) -> !transform.any_op
    transform.include @annotate_generic failures(propagate)  (%matmul)
      : (!transform.any_op) -> ()

    transform.yield
  }

  transform.named_sequence @match_generic(
      %entry: !transform.any_op {transform.readonly}) -> !transform.any_op {
    transform.match.operation_name %entry ["linalg.generic"] : !transform.any_op
    transform.yield %entry : !transform.any_op
  }

  transform.named_sequence @annotate_generic(
     %matmul: !transform.any_op {transform.readonly}) {
       %attr_value = transform.param.constant @acc1 -> !transform.any_param
       transform.annotate %matmul "phs_acc" = %attr_value : !transform.any_op, !transform.any_param
       %bounds = transform.param.constant array<i64: 4> -> !transform.any_param
       transform.annotate %matmul "phs_array_bounds" = %bounds : !transform.any_op, !transform.any_param
       transform.yield
  }
}
