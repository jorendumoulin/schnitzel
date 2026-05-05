#include "dpi_memory.h"
#include "dynamic_memory.h"
#include "sim.h"
#include <argparse/argparse.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>

class PySim {
public:
  PySim(const std::vector<std::string> &program_args) {
    sim = std::make_unique<Sim>(program_args, "");
  }

  int run() { return sim->run(); }

  std::map<std::string, int> get_symbols() { return g_loader.get_symbols(); };

  void write_data(uint64_t addr, pybind11::bytes data) {
    std::string tmp = data; // bytes → string buffer
    g_dpi_memory.write_chunk(addr, tmp.size(), tmp.data());
  }

  pybind11::bytes read_data(uint64_t addr, size_t size) {
    std::vector<uint8_t> buf(size);
    g_dpi_memory.read_chunk(addr, size, buf.data());
    return pybind11::bytes(reinterpret_cast<char *>(buf.data()), buf.size());
  }

private:
  std::unique_ptr<Sim> sim;
};

namespace py = pybind11;

PYBIND11_MODULE(my_module, m) {
  py::class_<PySim>(m, "Sim")
      .def(py::init<const std::vector<std::string> &>(), py::arg("program"))
      .def("run", &PySim::run)
      .def("get_symbols", &PySim::get_symbols)
      .def("write_data", &PySim::write_data, py::arg("addr"), py::arg("data"))
      .def("read_data", &PySim::read_data, py::arg("addr"), py::arg("size"));
}
