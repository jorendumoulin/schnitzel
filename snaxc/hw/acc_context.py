from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from xdsl.context import Context
from xdsl.ir import Operation
from xdsl.parser import ModuleOp
from xdsl.traits import SymbolTable

from snaxc.dialects.accfg import AcceleratorOp
from snaxc.hw.system import Accelerator, Memory, System


@dataclass
class AccContext(Context):
    """
    Context that additionally allows to register and query accelerators
    """

    system: System = field(default_factory=lambda: System(Memory("default", 0, 0), []))

    def clone(self) -> "AccContext":
        return AccContext(
            self.allow_unregistered,
            self._loaded_dialects.copy(),
            self._loaded_ops.copy(),
            self._loaded_attrs.copy(),
            self._loaded_types.copy(),
            self._registered_dialects.copy(),
            self.system,
        )

    def get_optional_accelerator(self, name: str) -> Accelerator | None:
        """
        Get an operation class from its name if it exists.
        If the accelerator is not registered, raise an exception.
        """
        return next((a for a in self.system.iter_accelerators() if a.name == name), None)

    def get_acc(self, name: str) -> Accelerator:
        """
        Get an operation class from its name if it exists.
        If the accelerator is not registered, raise an exception.
        """
        if (accelerator := self.get_optional_accelerator(name)) is None:
            raise Exception(f"Accelerator {name} is not registered")
        return accelerator

    def get_all_accelerators(self) -> Sequence[Accelerator]:
        return list(self.system.iter_accelerators())

    def get_acc_op_from_module(self, name: str, module: ModuleOp) -> tuple[AcceleratorOp, Accelerator]:
        """
        Perform a symbol table lookup for the accelerator op in the IR
        and then get the corresponding the Accelerator interface from
        the accelerator registry.
        Returns both the looked up accelerator op and the Accelerator interface
        """
        acc_op = find_accelerator_op(module, name)
        if acc_op is None:
            raise Exception(
                f"Symbol Table lookup failed for accelerator '{name}'. "
                "Is the symbol declared by an accfg.accelerator op in the module?"
            )
        return acc_op, self.get_acc(acc_op.name_prop.string_value())

    @property
    def registered_accelerator_names(self) -> Iterable[str]:
        """
        Returns the names of all registered accelerators. Not valid across mutations of this object.
        """
        for accelerator in self.system.iter_accelerators():
            yield accelerator.name

    def get_memory(self, name: str) -> Memory:
        """
        Get a memory space by its name.
        Raises KeyError if the memory space is not registered.
        """
        memory = next((mem for mem in self.system.iter_mems() if mem.name == name), None)
        if memory is None:
            raise KeyError(f"Memory space '{name}' is not registered")
        return memory


def find_accelerator_op(op: Operation, accelerator_str: str) -> AcceleratorOp | None:
    """
    Finds the accelerator op with a given symbol name in the ModuleOp of
    a given operation. Returns None if not found.
    """

    # find the module op
    module_op = op
    while module_op and not isinstance(module_op, ModuleOp):
        module_op = module_op.parent_op()
    if not module_op:
        raise RuntimeError("Module Op not found")
    trait = module_op.get_trait(SymbolTable)
    assert trait is not None
    acc_op = trait.lookup_symbol(module_op, accelerator_str)
    assert isinstance(acc_op, AcceleratorOp | None)
    return acc_op
