/*
Copyright (c) 2022, Jairus Martin.
Distributed under the terms of the GPL v3 License.
The full license is in the file LICENSE, distributed with this software.
*/
#include "VoxelClient_VisDrawer.h"
#include <Standard_Handle.hxx>
#include <Voxel_Prs.hxx>
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_DECLARE_HOLDER_TYPE(T, opencascade::handle<T>, true);

PYBIND11_MODULE(extensions, mod) {
  py::object Voxel_Prs_Base =
      (py::object)py::module_::import("OCCT.Voxel").attr("Voxel_Prs");

  py::class_<VoxelClient_PrsGl, opencascade::handle<VoxelClient_PrsGl>>
      cls_VoxelClient_PrsGl(mod, "VoxelClient_PrsGl", Voxel_Prs_Base);
  cls_VoxelClient_PrsGl.def(py::init<>());

  py::class_<Voxel_VisData> cls_Voxel_VisData(mod, "Voxel_VisData",
                                              "Voxel Data");

  py::class_<VoxelClient_VisDrawer> cls_VoxelClient_VisDrawer(
      mod, "VoxelClient_VisDrawer", "Voxel Drawer");
  cls_VoxelClient_VisDrawer.def(py::init<Voxel_VisData *>(),
                                py::arg("theData"));
}
