import numpy as np

from sim import Simulator

sim = Simulator(["/home/joren/phd/schnitzel/tests/operators/gemm/build/gemm"])

print(sim.get_symbols())

np.random.seed(42)

a = np.random.randint(0, 10, (16, 16), dtype=np.int8)
b = np.random.randint(0, 10, (16, 16), dtype=np.int8)

c = a.astype(np.int32) @ b.astype(np.int32)
print(a)
print(b)
print(c)

print(hex(sim.get_symbols()["a_data"]))

sim.write_data(sim.get_symbols()["a_data"], a.tobytes())
sim.write_data(sim.get_symbols()["b_data"], b.tobytes())

sim.run()

result = sim.read_data(sim.get_symbols()["result"], 8)
# need to dereference the result pointer:
result_data = int(np.frombuffer(result, dtype=np.int32)[1])
result = sim.read_data(result_data, c.nbytes)
result = np.frombuffer(result, dtype=np.int32).reshape(c.shape)

if np.array_equal(result, c):
    print("Success!")
else:
    print("oh no!")
