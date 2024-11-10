import numpy as np
import re
from svgpathtools import svg2paths, Path
from shapely.geometry import Polygon
import trimesh
from shapely.geometry import LinearRing

# Load SVG file and filter paths to exclude text elements and paths with stroke width < 0.56px
paths, attributes = svg2paths('small.svg')

def get_stroke_width(attr):
    # Extract stroke width from 'style' attribute if it exists
    style = attr.get('style', '')
    match = re.search(r'stroke-width:([\d.]+)px', style)
    if match:
        return float(match.group(1))
    # Default to 0 if stroke-width is not defined
    return 0.0

# Filter paths based on stroke width >= 0.56
filtered_paths = [
    path for path, attr in zip(paths, attributes)
    if 'text' not in attr.get('tag', '')  # Exclude text elements
    and get_stroke_width(attr) <= 0.2    # Exclude paths with stroke width < 0.56px
]

# Function to convert SVG path to line segments (approximating curves with straight lines)
def path_to_line_segments(path, num_segments=50):
    line_segments = []
    
    # Go through each segment in the path and convert to line segments
    for segment in path:
        segment_type = segment.__class__.__name__
        
        if segment_type == "Line":
            # If it's already a line, just take the start and end points
            line_segments.append((segment.start.real, segment.start.imag))
            line_segments.append((segment.end.real, segment.end.imag))
        elif segment_type in ["CubicBezier", "QuadraticBezier"]:
            # If it's a curve (Bezier), approximate it with straight line segments
            for t in np.linspace(0, 1, num_segments):
                point = segment.point(t)
                line_segments.append((point.real, point.imag))
        elif segment_type == "Arc":
            # If it's an arc, sample it as well
            for t in np.linspace(0, 1, num_segments):
                point = segment.point(t)
                line_segments.append((point.real, point.imag))
                
    return line_segments

# Function to convert path data to a Polygon
def path_to_polygon(path):
    segments = path_to_line_segments(path)
    if len(segments) > 2:
        # Try to create a Polygon from the line segments
        print(f"Segments: {segments}")
        polygon = Polygon(segments)
        # Ensure the polygon is valid (some paths may not form valid polygons)
        if polygon.is_valid:
            return polygon
        else:
            print("Invalid polygon")
    return None

# Convert each path to a polygon and collect them
polygons = []
for path in filtered_paths:
    polygon = path_to_polygon(path)
    if polygon:
        print(f"Valid polygon: {polygon}")
        polygons.append(polygon)
    else:
        print(f"Invalid polygon for path: {path}")

# Function to extrude a polygon by a height
def extrude_polygon(polygon, height=300):
    # Get the exterior coordinates of the polygon
    coords = list(polygon.exterior.coords)
    
    # Create a 3D mesh by extruding the 2D polygon along the z-axis
    base_mesh = trimesh.creation.extrude_polygon(polygon, height)
    
    if base_mesh.is_empty:
        print(f"Extrusion failed for polygon: {polygon}")
    return base_mesh

# Extrude each polygon and collect the 3D meshes
extrusions = []
for poly in polygons:
    extrusion = extrude_polygon(poly, height=300)
    if not extrusion.is_empty:
        extrusions.append(extrusion)
    else:
        print(f"Empty extrusion for polygon: {poly}")

# Combine all extrusions into one mesh
try:
    final_mesh = trimesh.util.concatenate(extrusions)
    if final_mesh.is_empty:
        print("Error: The final mesh is empty!")
    else:
        # Export the final 3D mesh to an STL file
        final_mesh.export('extruded_floorplan1.stl')
        # Visualize the extruded floor plan
        final_mesh.show()

except Exception as e:
    print(f"Error while concatenating meshes: {e}")