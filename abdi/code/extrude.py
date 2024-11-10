import trimesh
import svgpathtools
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from collections import deque
import time

# Paths for input and output files
input_svg_path = './simpler floors/floor1_clean.svg'
output_path = './3d models/floor1.glb'  # Changed to .glb for opacity support
extrusion_height = 35.088

# Define a translucent color for the walls
opacity = 0.15  # 85% translucent
material_color = [0.5, 0.5, 0.5, opacity]  # RGBA format with 85% translucency

def is_degenerate_path(path):
    """Check if a path is degenerate (zero length or single point)."""
    if isinstance(path, svgpathtools.Line):
        return abs(path.start - path.end) < 1e-6
    return path.length() < 1e-6

def svg_to_wall_polygons(svg_path, num_points=100):
    polygons = []
    svg_paths, _ = svgpathtools.svg2paths(svg_path)
    
    for path in svg_paths:
        if is_degenerate_path(path):
            continue
            
        points = []
        try:
            if len(path) == 1 and isinstance(path[0], svgpathtools.Line):
                segment = path[0]
                points.append([segment.start.real, segment.start.imag])
                points.append([segment.end.real, segment.end.imag])
            else:
                total_length = path.length()
                if total_length < 1e-6:
                    continue
                    
                num_samples = max(int(total_length / 10), num_points)
                sample_points = np.linspace(0, 1, num_samples)
                
                for t in sample_points:
                    point = path.point(t)
                    points.append([point.real, point.imag])
            
            if len(points) >= 2:
                if np.linalg.norm(np.array(points[0]) - np.array(points[-1])) > 1e-6:
                    points.append(points[0])
                
                points = np.array(points)
                unique_mask = np.ones(len(points), dtype=bool)
                unique_mask[1:] = np.any(np.abs(points[1:] - points[:-1]) > 1e-6, axis=1)
                points = points[unique_mask]
                
                if len(points) >= 3:
                    polygons.append(points)
                    
        except Exception as e:
            print(f"Skipping problematic path: {e}")
            continue
    
    return connect_nearby_endpoints(polygons) if polygons else []

def connect_nearby_endpoints(polygons, threshold=1.0):
    """
    Iteratively connect walls that have endpoints close to each other.
    """
    if not polygons:
        return []
    
    poly_data = []
    for i, poly in enumerate(polygons):
        if len(poly) >= 2:
            poly_data.append({
                'index': i,
                'start': poly[0],
                'end': poly[-1],
                'points': poly,
                'used': False
            })
    
    if not poly_data:
        return polygons
    
    endpoints = []
    endpoint_indices = []
    for i, data in enumerate(poly_data):
        endpoints.extend([data['start'], data['end']])
        endpoint_indices.extend([i, i])
    
    endpoints = np.array(endpoints)
    tree = cKDTree(endpoints)
    pairs = list(tree.query_pairs(threshold))
    
    connections = {}
    for p1, p2 in pairs:
        poly1_idx = endpoint_indices[p1]
        poly2_idx = endpoint_indices[p2]
        
        if poly1_idx != poly2_idx:
            if poly1_idx not in connections:
                connections[poly1_idx] = set()
            if poly2_idx not in connections:
                connections[poly2_idx] = set()
            connections[poly1_idx].add(poly2_idx)
            connections[poly2_idx].add(poly1_idx)
    
    merged_polygons = []
    for start_idx in range(len(poly_data)):
        if poly_data[start_idx]['used']:
            continue
        
        current_chain = []
        queue = deque([(start_idx, poly_data[start_idx]['points'], False)])
        poly_data[start_idx]['used'] = True
        
        while queue:
            current_idx, current_points, reverse_current = queue.popleft()
            if reverse_current:
                current_points = np.flip(current_points, axis=0)
            
            current_chain.append(current_points)
            
            if current_idx in connections:
                end_point = current_points[-1]
                
                for next_idx in connections[current_idx]:
                    if not poly_data[next_idx]['used']:
                        next_poly = poly_data[next_idx]['points']
                        start_dist = np.linalg.norm(end_point - next_poly[0])
                        end_dist = np.linalg.norm(end_point - next_poly[-1])
                        reverse_next = end_dist < start_dist
                        queue.append((next_idx, next_poly, reverse_next))
                        poly_data[next_idx]['used'] = True
        
        if current_chain:
            merged = current_chain[0]
            for next_poly in current_chain[1:]:
                connection_point = (merged[-1] + next_poly[0]) / 2
                merged = np.vstack((merged[:-1], [connection_point], next_poly[1:]))
            if len(merged) >= 3:
                merged_polygons.append(merged)
    
    return merged_polygons

def merge_and_extrude_polygons(polygons, height):
    if not polygons:
        raise ValueError("No valid polygons to process")
        
    shapely_polygons = []
    for poly in polygons:
        try:
            lines = []
            for i in range(len(poly) - 1):
                p1, p2 = poly[i], poly[i + 1]
                if np.linalg.norm(p2 - p1) > 1e-6:
                    line = LineString([p1, p2])
                    line = line.simplify(0.05)  # Simplify the line to reduce complexity
                    lines.append(line)
            
            if lines:
                buffered_lines = [line.buffer(0.05, cap_style=2, join_style=2) for line in lines]
                merged_lines = unary_union(buffered_lines)
                
                if merged_lines.is_valid and not merged_lines.is_empty:
                    shapely_polygons.append(merged_lines)
                    
        except Exception as e:
            print(f"Skipping invalid polygon: {e}")
            continue
    
    if not shapely_polygons:
        raise ValueError("No valid polygons to process after cleanup")
    
    united_polygon = unary_union(shapely_polygons)
    
    if isinstance(united_polygon, MultiPolygon):
        meshes = []
        for poly in united_polygon.geoms:
            if poly.is_valid and not poly.is_empty:
                mesh = trimesh.creation.extrude_polygon(poly, height, cap=True)
                meshes.append(mesh)
        if meshes:
            final_mesh = trimesh.util.concatenate(meshes)
        else:
            raise ValueError("No valid meshes created")
    else:
        final_mesh = trimesh.creation.extrude_polygon(united_polygon, height, cap=True)
    
    # Apply opacity to the walls and ensure it's exported properly in GLB format
    final_mesh.visual = trimesh.visual.ColorVisuals(mesh=final_mesh, face_colors=material_color)
    
    # Add a manual floor at the base of the mesh
    floor_polygons = []
    if isinstance(united_polygon, MultiPolygon):
        floor_polygons.extend(united_polygon.geoms)
    else:
        floor_polygons.append(united_polygon)

    floor_meshes = [trimesh.creation.extrude_polygon(poly, 0.1) for poly in floor_polygons if poly.is_valid and not poly.is_empty]
    for floor_mesh in floor_meshes:
        floor_mesh.visual = trimesh.visual.ColorVisuals(mesh=floor_mesh, face_colors=material_color)
    
    combined_mesh = trimesh.util.concatenate([*floor_meshes, final_mesh])
    
    return combined_mesh

try:
    start_time = time.time()
    wall_polygons = svg_to_wall_polygons(input_svg_path)
    
    if not wall_polygons:
        raise ValueError("No valid polygons extracted from SVG")
    
    solid_mesh = merge_and_extrude_polygons(wall_polygons, extrusion_height)
    solid_mesh.export(output_path)  # Export as GLB for transparency support
    print(f"Successfully exported solid 3D model with nearly translucent opacity to {output_path}")
    print(f"Total execution time: {time.time() - start_time:.2f} seconds")
    
except Exception as e:
    print(f"Error processing SVG: {e}")