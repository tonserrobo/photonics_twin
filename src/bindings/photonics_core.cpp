#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "photonics/materials.hpp"
#include "photonics/bragg.hpp"
#include "photonics/tmm.hpp"

namespace py = pybind11;
using photonics::Material;
using photonics::SellmeierCoeffs;
using photonics::BraggGrating;
using photonics::LayerStack;

PYBIND11_MODULE(photonics_core, m) {
    m.doc() = "SPEAR Photonics Digital Twin — C++ core (Bragg slice)";
    m.attr("__version__") = "0.1.0";

    py::class_<SellmeierCoeffs>(m, "SellmeierCoeffs")
        .def(py::init<double, double, double, double, double, double>(),
             py::arg("B1"), py::arg("B2"), py::arg("B3"),
             py::arg("C1"), py::arg("C2"), py::arg("C3"));

    py::class_<Material>(m, "Material")
        .def(py::init<std::string, SellmeierCoeffs>(),
             py::arg("name"), py::arg("coeffs"))
        .def("n", &Material::n, py::arg("wavelength_nm"))
        .def_property_readonly("name", &Material::name);

    py::class_<BraggGrating>(m, "BraggGrating")
        .def(py::init<Material, Material, double, std::size_t>(),
             py::arg("high"), py::arg("low"),
             py::arg("centre_nm"), py::arg("periods"))
        .def("set_centre_nm", &BraggGrating::set_centre_nm)
        .def("set_periods",   &BraggGrating::set_periods)
        .def_property_readonly("centre_nm", &BraggGrating::centre_nm)
        .def_property_readonly("periods",   &BraggGrating::periods)
        .def("reflectance",
             [](const BraggGrating& self, py::array_t<double, py::array::c_style> wl) {
                 auto buf = wl.request();
                 if (buf.ndim != 1) throw std::runtime_error("wavelengths must be 1-D");
                 const std::size_t n = static_cast<std::size_t>(buf.shape[0]);
                 py::array_t<double> R(static_cast<py::ssize_t>(n));
                 self.reflectance(static_cast<const double*>(buf.ptr), n,
                                  static_cast<double*>(R.request().ptr));
                 return R;
             }, py::arg("wavelengths_nm"))
        .def("stack_view",
             [](const BraggGrating& self) {
                 const auto& s = self.stack();
                 const double centre = static_cast<double>(self.centre_nm());
                 py::list out;
                 for (std::size_t i = 0; i < s.size(); ++i) {
                     const auto& L = s.at(i);
                     py::dict d;
                     d["index"]        = static_cast<int>(i);
                     d["material"]     = L.material->name();
                     d["thickness_nm"] = static_cast<double>(L.thickness_nm);
                     d["n_at_centre"]  = static_cast<double>(L.material->n(centre));
                     out.append(d);
                 }
                 return out;
             });
}
