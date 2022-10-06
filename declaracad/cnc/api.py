import enaml

from declaracad.cnc.operation import Operation

with enaml.imports():
    from declaracad.cnc.cutters import (
        ChamferMill,
        EndMill,
        FaceMill,
        ThreadMill,
        Tool,
        TwistDrill,
    )
    from declaracad.cnc.operations.chamfer import ChamferOperation
    from declaracad.cnc.operations.contour import ContourOperation
    from declaracad.cnc.operations.drilling import DrillingCycle
    from declaracad.cnc.operations.facing import FacingOperation
    from declaracad.cnc.operations.job import Job, JobSimulation
    from declaracad.cnc.operations.pocket import (
        CircularPocketData,
        CircularPocketOperation,
        PocketData,
        PocketOperation,
    )
    from declaracad.cnc.operations.sidecut import SideCutOperation
    from declaracad.cnc.operations.slotting import SlottingOperation
    from declaracad.cnc.operations.threading import ThreadingData, ThreadingOperation
