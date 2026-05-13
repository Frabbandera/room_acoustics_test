"""
Pyroomacoustics room builders for the Room Acoustics backend.
3D Version - Final Fixed Version for Type Compatibility.
"""

import numpy as np
import pyroomacoustics as pra
import shared.result_keys as RK
import shared.scene_keys as SK

def build_pra_room(cfg, *, ray_tracing=False, ray_tracing_kwargs=None):
    walls = []
    
    for i, face in enumerate(cfg["faces"]):
        surface_type = face["surface_type"]
        
        # Recupera i coefficienti
        abs_val = cfg[f"{surface_type}_abs"]
        scat_val = cfg[f"{surface_type}_scat"]
        
        # FIX CRITICO: Pyroomacoustics vuole array per absorption e scattering, 
        # anche se è un singolo valore.
        abs_coeff = np.array([abs_val], dtype=np.float32)
        scat_coeff = np.array([scat_val], dtype=np.float32)
        
        # Vertici come (3, N)
        corners = np.array(face["vertices"], dtype=np.float32).T
        
        # Creazione del muro con i tipi dati corretti
        wall = pra.wall_factory(
            corners,
            absorption=abs_coeff,
            scattering=scat_coeff,
            name=f"{surface_type}_{i}"
        )
        walls.append(wall)

    room_kwargs = {
        "walls": walls,
        "fs": cfg["fs"],
        "max_order": cfg["max_order"],
        "air_absorption": cfg["air_absorption"],
    }

    if ray_tracing:
        room_kwargs["ray_tracing"] = True

    room = pra.Room(**room_kwargs)

    if ray_tracing:
        rt_kwargs = dict(ray_tracing_kwargs or {})
        room.set_ray_tracing(**rt_kwargs)

    return room

def add_sources_to_room(room, sources):
    source_names = []
    for source in sources:
        source_name = source[SK.NAME]
        source_position = np.array(source[SK.POSITION], dtype=float)
        
        if not room.is_inside(source_position, include_borders=True):
            raise ValueError(f"Source {source_name} is outside the 3D room.")
            
        room.add_source(source_position)
        source_names.append(source_name)
    return source_names

def add_microphones_to_room(room, flat_receivers):
    if not flat_receivers:
        return
    mic_positions = np.array(
        [receiver[RK.POSITION] for receiver in flat_receivers],
        dtype=float,
    ).T
    room.add_microphone_array(mic_positions)
