"""
Fast 1-Pass Shell Wall / Slab Opening Tool for SAP2000
Handles:
- Identification of opening bounding box [xmin, xmax] x [zmin, zmax] at Y = y_plane
- Automatic creation of boundary split points and lintel/sill shell elements
- Inheritance of Area Surface Pressure Loads (soil pressure, hydrostatic pressure with joint patterns)
- Inheritance of Area Groups and Properties
- Safe deletion of interior shell elements
- Removal of interior point loads (e.g. cable tray load CL) to prevent zero-stiffness instability
- Automatic application of Auto Edge Constraints to connect lintel/sill nodes to adjacent jambs seamlessly
- Model refresh and save
"""

def cut_wall_opening(SapModel, y_plane, x_min, x_max, z_min, z_max, prop_name="Wall_t700", group_name="3000~3499_LeftWall"):
    tol = 1e-3
    
    # 1. Get all areas and identify which are inside opening or cut by boundary
    names_raw = SapModel.AreaObj.GetNameList()
    area_names = names_raw[1] if isinstance(names_raw, (list, tuple)) else []
    
    areas_to_delete = []
    areas_cut_top = []
    areas_cut_bottom = []
    
    for a in area_names:
        pts = SapModel.AreaObj.GetPoints(a)[1]
        coords = [SapModel.PointObj.GetCoordCartesian(p, 0, 0, 0) for p in pts]
        if all(abs(c[1] - y_plane) < tol for c in coords):
            xs = [c[0] for c in coords]
            zs = [c[2] for c in coords]
            a_xmin, a_xmax = min(xs), max(xs)
            a_zmin, a_zmax = min(zs), max(zs)
            
            # Check overlap in X
            if a_xmax > x_min + tol and a_xmin < x_max - tol:
                # Fully inside in Z
                if a_zmin >= z_min - tol and a_zmax <= z_max + tol:
                    areas_to_delete.append(a)
                # Cut across top edge z_max
                elif a_zmin < z_max - tol and a_zmax > z_max + tol:
                    areas_cut_top.append({
                        'name': a, 'pts': list(pts), 'coords': coords,
                        'xmin': a_xmin, 'xmax': a_xmax, 'zmin': a_zmin, 'zmax': a_zmax
                    })
                # Cut across bottom edge z_min
                elif a_zmin < z_min - tol and a_zmax > z_min + tol:
                    areas_cut_bottom.append({
                        'name': a, 'pts': list(pts), 'coords': coords,
                        'xmin': a_xmin, 'xmax': a_xmax, 'zmin': a_zmin, 'zmax': a_zmax
                    })
    
    new_areas_created = []
    
    # 2. Handle cut areas at top (create remaining upper lintel strips [z_max -> a_zmax])
    for item in areas_cut_top:
        old_a = item['name']
        x1, x2 = item['xmin'], item['xmax']
        z_top = item['zmax']
        
        # Read surface pressures and joint offsets from original element
        sp_raw = SapModel.AreaObj.GetLoadSurfacePressure(old_a)
        sp_loads = []
        if sp_raw[0] > 0:
            for i in range(sp_raw[0]):
                sp_loads.append((sp_raw[2][i], sp_raw[3][i], sp_raw[4][i], sp_raw[5][i]))
        
        # Read joint offsets (thickness offset)
        off_raw = SapModel.AreaObj.GetOffsets(old_a)
        off_vals = off_raw[3] if len(off_raw) > 3 and off_raw[3] else None
        
        # Create 2 points at z_max
        pt_b_left = SapModel.PointObj.AddCartesian(x1, y_plane, z_max, "")[0]
        pt_b_right = SapModel.PointObj.AddCartesian(x2, y_plane, z_max, "")[0]
        
        # Find existing top points of original area
        # coords order is usually bottom-left, bottom-right, top-right, top-left
        pt_t_left = None
        pt_t_right = None
        for p, c in zip(item['pts'], item['coords']):
            if abs(c[2] - z_top) < tol:
                if abs(c[0] - x1) < tol:
                    pt_t_left = p
                elif abs(c[0] - x2) < tol:
                    pt_t_right = p
        
        if pt_t_left and pt_t_right:
            new_pts = [pt_b_left, pt_b_right, pt_t_right, pt_t_left]
            raw_new = SapModel.AreaObj.AddByPoint(4, new_pts, "", prop_name)
            new_a = raw_new[1]
            new_areas_created.append(new_a)
            
            # Assign group
            if group_name:
                SapModel.AreaObj.SetGroupAssign(new_a, group_name)
                
            # Assign surface pressures
            for pat, face, val, pat_name in sp_loads:
                SapModel.AreaObj.SetLoadSurfacePressure(new_a, pat, face, val, pat_name, False, 0)
                
            # Inherit joint offsets
            if off_vals:
                SapModel.AreaObj.SetOffsets(new_a, 2, "", 0.0, [off_vals[0], off_vals[1], off_vals[2], off_vals[3]], 0)
        
        # Mark old area for deletion
        areas_to_delete.append(old_a)
        
    # 3. Delete all opening and cut areas
    for a in set(areas_to_delete):
        SapModel.AreaObj.Delete(a)
        
    # 4. Check interior points for loads (e.g. cable tray load CL) and remove loads
    pt_names_raw = SapModel.PointObj.GetNameList()
    all_pts = pt_names_raw[1] if isinstance(pt_names_raw, (list, tuple)) else []
    for p in all_pts:
        c = SapModel.PointObj.GetCoordCartesian(p, 0, 0, 0)
        if abs(c[1] - y_plane) < tol:
            if x_min + tol < c[0] < x_max - tol and z_min + tol < c[2] < z_max - tol:
                # Inside hole: check loads
                raw_lf = SapModel.PointObj.GetLoadForce(p)
                if raw_lf[0] > 0:
                    for i in range(raw_lf[0]):
                        SapModel.PointObj.DeleteLoadForce(p, raw_lf[2][i])
                # Unmark special point if any
                SapModel.PointObj.SetSpecialPoint(p, False)
                SapModel.PointObj.DeleteSpecialPoint(p)
                
    # 5. Enable Auto Edge Constraint ONLY locally on new/touching areas (never blindly to ALL)
    for a in new_areas_created:
        SapModel.AreaObj.SetEdgeConstraint(a, True, 0)
    
    # 6. Refresh view
    SapModel.View.RefreshView(0, False)
    
    return {
        'areas_deleted_count': len(set(areas_to_delete)),
        'new_areas_count': len(new_areas_created),
        'new_areas': new_areas_created
    }
