import numpy as np

ruta_archivo = 'depth_map.npy'
try:
    depth_orig = np.load(ruta_archivo)
    print(f"Dimensiones originales: {depth_orig.shape}")
except FileNotFoundError:
    print("No se encontró el archivo .npy")
    exit()


repeticiones_largo = 15
repeticiones_ancho = 15


depth_extendido = np.tile(depth_orig, (repeticiones_largo, repeticiones_ancho))

print(f"Nuevas dimensiones: {depth_extendido.shape}")

np.save('depth_map_conc.npy', depth_extendido)
print("Archivo guardado con éxito como 'depth_map_conc.npy'")