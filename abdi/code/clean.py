import trimesh
import numpy as np

# Load the GLB file
mesh = trimesh.load('./3d models/stacked_floors_with_bases.glb')

# Define function to identify floor plans based on geometry
def identify_floors(mesh, height_threshold=0.2, area_threshold=10):
    floors = []
    for name, geom in mesh.geometry.items():
        # Check geometry bounds and area
        bounds = geom.bounds
        height = bounds[1][2] - bounds[0][2]  # Z-axis height difference
        
        # Debug: Print geometry name, area, and height
        print(f"Geometry: {name}, Area: {geom.area}, Height: {height}")
        
        # Identify flat and large enough areas as floors
        if height < height_threshold and geom.area > area_threshold:
            floors.append(geom)
    
    # Debug: Check number of floors found
    print(f"Number of floors identified: {len(floors)}")
    return floors

# Attempt to identify floor plans
floors = identify_floors(mesh)

# If floors are identified, create a new scene
if floors:
    floor_scene = trimesh.Scene(floors)
    floor_scene.export('./3d models/floor_plans_cleaned.glb')
    print("Exported cleaned floor plans to 'floor_plans_cleaned.glb'")
else:
    print("No floor plans identified. Consider adjusting thresholds.")