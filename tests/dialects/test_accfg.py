from xdsl.dialects import builtin, test
from xdsl.dialects.builtin import StringAttr

from snaxc.dialects import accfg


def test_acc_setup():
    one, two = test.TestOp(result_types=[builtin.i32, builtin.i32]).results

    setup1 = accfg.SetupOp({"A": one, "B": two}, "acc1")
    setup1.verify()

    assert setup1.accelerator == StringAttr("acc1")

    setup2 = accfg.SetupOp(dict(setup1.iter_params()), setup1.accelerator, setup1)
    setup2.verify()

    assert setup2.accelerator == setup1.accelerator
    assert isinstance(setup2.out_state.type, accfg.StateType)
    assert setup2.out_state.type.accelerator == setup1.accelerator
