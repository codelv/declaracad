from .api import Wire


def discontinous_points(wire, tol=0.5):
    """Find points of discontinuity of a wire

    Parameters
    ----------
    wire: TopoDS_Wire
        The wire to find corner points of
    tol: Float
        The tolerance to use

    Returns
    -------
    points: List[Point]
        List of points where there is C1 discontinuity

    """
    w = Wire(edges=[wire])
    w.render()
    points = []

    # Map of vertex to map of curve an derivative
    data = {}

    for p in w.topology.points:
        # points.append({'color': 'white', 'position': p})
        data[p] = []
    for d in w.topology.curves:
        curve = d["curve"]
        for t in (curve.FirstParameter(), curve.LastParameter()):
            p, v = Topology.get_value_at(curve, t=t, derivative=1)
            r = data.get(p)
            if r is None:
                # Need to lookup different points with equal values
                for k in data:
                    if k.is_equal(p):
                        r = data[k]
                        break
                if r is None:
                    data[p] = []
                # points.append({'color': 'blue', 'position': p})
                # continue # Ignore intermediate point
            r.append((curve, v))

    for p, curves in data.items():
        if len(curves) < 2:
            points.append({"color": "purple", "position": p})
            continue

        v1, v2 = curves[0][1], curves[1][1]
        if v1.is_parallel(v2, tol):
            continue  # Continuous
        points.append({"color": "red", "position": p})

    return points
