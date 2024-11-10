import trimesh
import numpy as np

# File paths
file_paths = [
    './3d models/floor1.glb',
    './3d models/floor2.glb',
    './3d models/floor3.glb',
    './3d models/floor4.glb',
    './3d models/floor5.glb',
    './3d models/floor6.glb',
]

# Parameters
height_offset = 10

# Create meshes list
meshes = []

for i, file_path in enumerate(file_paths):
    # Load and process floor mesh
    floor_mesh = trimesh.load(file_path)
    floor_mesh.apply_scale([1, 1, 6])
    floor_mesh.apply_translation([0, 0, height_offset * i])
    
    # Double the opacity by adjusting the alpha channel of the materials
    if hasattr(floor_mesh, 'visual') and hasattr(floor_mesh.visual, 'material'):
        if hasattr(floor_mesh.visual.material, 'baseColorFactor'):
            current_color = floor_mesh.visual.material.baseColorFactor
            # Double the opacity (alpha channel) while keeping it capped at 1.0
            new_alpha = min(1.0, current_color[3] * 2)
            floor_mesh.visual.material.baseColorFactor = [
                current_color[0],
                current_color[1],
                current_color[2],
                new_alpha
            ]
    
    meshes.append(floor_mesh)
    
# Combine all meshes into a single scene
combined = trimesh.util.concatenate(meshes)

# Export the combined model
combined.export('./3d models/stacked_floors_with_bases.glb')