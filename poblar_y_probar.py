"""
Script de prueba: pobla la base de datos con personajes de ejemplo
y ejecuta una batalla de demostración.
Ejecutar con: python poblar_y_probar.py
"""
import requests

BASE = "http://127.0.0.1:8000"

personajes = [
    {"nombre": "Thorin Escudoderoble", "color_piel": "bronceado", "raza": "enano",
     "fuerza": 90, "agilidad": 40, "magia": 15, "conocimiento": 60},
    {"nombre": "Arwen Undómiel",       "color_piel": "pálido",    "raza": "elfo",
     "fuerza": 55, "agilidad": 95, "magia": 80, "conocimiento": 85},
    {"nombre": "Saruman el Blanco",    "color_piel": "claro",     "raza": "mago",
     "fuerza": 40, "agilidad": 35, "magia": 99, "conocimiento": 98},
    {"nombre": "Gimli",                "color_piel": "rojizo",    "raza": "enano",
     "fuerza": 88, "agilidad": 45, "magia": 5,  "conocimiento": 50},
]

ids = []
for p in personajes:
    r = requests.post(f"{BASE}/personajes", json=p)
    data = r.json()
    ids.append(data["id"])
    print(f"  ✅ Creado: {data['nombre']} (ID={data['id']})")

print("\n⚔️  Batalla: Thorin vs Arwen")
r = requests.post(f"{BASE}/batalla", json={"id_personaje_1": ids[0], "id_personaje_2": ids[1]})
resultado = r.json()
print(f"  🏆 Ganador: {resultado['ganador']}")
print(f"  📋 Resumen: {resultado['resumen']}")

print("\n⚔️  Batalla: Saruman vs Gimli")
r = requests.post(f"{BASE}/batalla", json={"id_personaje_1": ids[2], "id_personaje_2": ids[3]})
resultado = r.json()
print(f"  🏆 Ganador: {resultado['ganador']}")
print(f"  📋 Resumen: {resultado['resumen']}")
