import os
from pathlib import Path

# custom_ops.py
import torch
import torch.nn as nn
import torch.nn.functional as F
from executorch.extension.export_util.utils import export_to_exec_prog, save_pte_program
from torch.export import export
from torch.library import Library, impl


my_op_lib = Library("my_ops", "DEF")

# registering an operator that multiplies input tensor by 3 and returns it.
my_op_lib.define("mul3(Tensor input) -> Tensor")  # should print 'mul3'


@impl(my_op_lib, "mul3", dispatch_key="CompositeExplicitAutograd")
def mul3_impl(a: torch.Tensor) -> torch.Tensor:
    return a


# registering the out variant.
my_op_lib.define(
    "mul3.out(Tensor input, *, Tensor(a!) output) -> Tensor(a!)"
)  # should print 'mul3.out'


@impl(my_op_lib, "mul3.out", dispatch_key="CompositeExplicitAutograd")
def mul3_out_impl(a: torch.Tensor, *, out: torch.Tensor) -> torch.Tensor:
    out.copy_(a)
    return out


class HelloWorldModel(nn.Module):
    def __init__(self, input_dim=10, hidden_dim=8, output_dim=3):
        super(HelloWorldModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = torch.ops.my_ops.mul3.default(x)
        x = self.fc2(x)
        x = F.softmax(x, dim=-1)  # Softmax over last dimension
        return x


model = HelloWorldModel()
model.eval()  # Set to evaluation mode
example_input = torch.tensor([1.0, 0.5, 3.2, 5.6, 2.1, -3.4, 0.7, -0.13, -0.88, 0.22])

print(f"Input shape: {example_input.shape}")
print(f"Input values: {example_input.squeeze().tolist()}")

# Run inference
print("\n=== Running Inference ===")
with torch.no_grad():
    output = model(example_input)

print(f"Output shape: {output.shape}")
print(f"Output probabilities: {output.squeeze().tolist()}")

print(export(model, (example_input,)).graph)

prog = export_to_exec_prog(model, (example_input,))
save_pte_program(prog, "model")
