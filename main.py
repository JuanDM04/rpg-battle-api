from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import Optional
import random

# ──────────────────────────────────────────────
#  Base de datos
# ──────────────────────────────────────────────
DATABASE_URL = "sqlite:///./rpg.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ──────────────────────────────────────────────
#  Modelo ORM
# ──────────────────────────────────────────────
class PersonajeDB(Base):
    __tablename__ = "personajes"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String, nullable=False)
    color_piel  = Column(String, nullable=False)
    raza        = Column(String, nullable=False)
    fuerza      = Column(Integer, default=10)
    agilidad    = Column(Integer, default=10)
    magia       = Column(Integer, default=10)
    conocimiento= Column(Integer, default=10)

Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────────
#  Esquemas Pydantic
# ──────────────────────────────────────────────
class PersonajeBase(BaseModel):
    nombre:       str = Field(..., example="Aragorn")
    color_piel:   str = Field(..., example="claro")
    raza:         str = Field(..., example="humano")
    fuerza:       int = Field(10, ge=1, le=100, example=80)
    agilidad:     int = Field(10, ge=1, le=100, example=65)
    magia:        int = Field(10, ge=1, le=100, example=20)
    conocimiento: int = Field(10, ge=1, le=100, example=70)

class PersonajeCreate(PersonajeBase):
    pass

class PersonajeUpdate(BaseModel):
    nombre:       Optional[str] = None
    color_piel:   Optional[str] = None
    raza:         Optional[str] = None
    fuerza:       Optional[int] = Field(None, ge=1, le=100)
    agilidad:     Optional[int] = Field(None, ge=1, le=100)
    magia:        Optional[int] = Field(None, ge=1, le=100)
    conocimiento: Optional[int] = Field(None, ge=1, le=100)

class PersonajeResponse(PersonajeBase):
    id: int
    class Config:
        from_attributes = True

class BatallaRequest(BaseModel):
    id_personaje_1: int = Field(..., example=1)
    id_personaje_2: int = Field(..., example=2)

# ──────────────────────────────────────────────
#  Dependencia de sesión
# ──────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ──────────────────────────────────────────────
#  Lógica de combate
# ──────────────────────────────────────────────
def calcular_poder(p: PersonajeDB) -> dict:
    """
    Fórmula de poder de combate:
      - Daño físico  = fuerza  × 1.5  + varianza aleatoria (±10 %)
      - Evasión      = agilidad × 0.8
      - Ataque mágico= magia   × 1.2
      - Bonus estratégico = conocimiento × 0.5
      - Poder total  = daño_fisico + ataque_magico + bonus - evasión_rival
        (la evasión se aplica en el cálculo de rondas)
    """
    varianza = random.uniform(0.9, 1.1)
    daño_fisico   = round(p.fuerza    * 1.5  * varianza, 2)
    evasion       = round(p.agilidad  * 0.8,             2)
    ataque_magico = round(p.magia     * 1.2  * varianza, 2)
    bonus         = round(p.conocimiento * 0.5,          2)
    poder_total   = round(daño_fisico + ataque_magico + bonus, 2)
    return {
        "daño_fisico":   daño_fisico,
        "evasion":       evasion,
        "ataque_magico": ataque_magico,
        "bonus_estrategia": bonus,
        "poder_total":   poder_total,
    }

def simular_batalla(p1: PersonajeDB, p2: PersonajeDB) -> dict:
    stats1 = calcular_poder(p1)
    stats2 = calcular_poder(p2)

    # El poder efectivo descuenta la evasión del rival
    efectivo1 = max(0, stats1["poder_total"] - stats2["evasion"])
    efectivo2 = max(0, stats2["poder_total"] - stats1["evasion"])

    if efectivo1 > efectivo2:
        ganador, perdedor = p1, p2
        margen = round(efectivo1 - efectivo2, 2)
    elif efectivo2 > efectivo1:
        ganador, perdedor = p2, p1
        margen = round(efectivo2 - efectivo1, 2)
    else:
        ganador = perdedor = None  # empate
        margen = 0

    resumen_combate = (
        f"{'EMPATE' if not ganador else ganador.nombre + ' venció a ' + perdedor.nombre}. "
        f"Poder efectivo — {p1.nombre}: {efectivo1} pts | {p2.nombre}: {efectivo2} pts. "
        f"Margen de victoria: {margen} pts."
    )

    return {
        "ganador": ganador.nombre if ganador else "EMPATE",
        "perdedor": perdedor.nombre if perdedor else "EMPATE",
        "puntaje_personaje_1": {
            "nombre": p1.nombre,
            "poder_efectivo": efectivo1,
            "desglose": stats1,
        },
        "puntaje_personaje_2": {
            "nombre": p2.nombre,
            "poder_efectivo": efectivo2,
            "desglose": stats2,
        },
        "resumen": resumen_combate,
    }

# ──────────────────────────────────────────────
#  Aplicación FastAPI
# ──────────────────────────────────────────────
app = FastAPI(
    title="RPG Battle API",
    description="API REST para gestión de personajes y simulación de batallas en un juego de rol.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── CRUD Personajes ───────────────────────────

@app.post("/personajes", response_model=PersonajeResponse, status_code=201,
          summary="Crear personaje", tags=["Personajes"])
def crear_personaje(personaje: PersonajeCreate, db: Session = Depends(get_db)):
    db_obj = PersonajeDB(**personaje.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.get("/personajes", response_model=list[PersonajeResponse],
         summary="Listar todos los personajes", tags=["Personajes"])
def listar_personajes(db: Session = Depends(get_db)):
    return db.query(PersonajeDB).all()


@app.get("/personajes/{personaje_id}", response_model=PersonajeResponse,
         summary="Consultar personaje por ID", tags=["Personajes"])
def obtener_personaje(personaje_id: int, db: Session = Depends(get_db)):
    obj = db.query(PersonajeDB).filter(PersonajeDB.id == personaje_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    return obj


@app.put("/personajes/{personaje_id}", response_model=PersonajeResponse,
         summary="Actualizar personaje", tags=["Personajes"])
def actualizar_personaje(personaje_id: int, datos: PersonajeUpdate,
                         db: Session = Depends(get_db)):
    obj = db.query(PersonajeDB).filter(PersonajeDB.id == personaje_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    for campo, valor in datos.model_dump(exclude_none=True).items():
        setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/personajes/{personaje_id}", status_code=204,
            summary="Eliminar personaje", tags=["Personajes"])
def eliminar_personaje(personaje_id: int, db: Session = Depends(get_db)):
    obj = db.query(PersonajeDB).filter(PersonajeDB.id == personaje_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    db.delete(obj)
    db.commit()

# ── Sistema de Batallas ───────────────────────

@app.post("/batalla", summary="Simular batalla entre dos personajes", tags=["Batalla"])
def batalla(request: BatallaRequest, db: Session = Depends(get_db)):
    p1 = db.query(PersonajeDB).filter(PersonajeDB.id == request.id_personaje_1).first()
    p2 = db.query(PersonajeDB).filter(PersonajeDB.id == request.id_personaje_2).first()

    if not p1:
        raise HTTPException(status_code=404, detail=f"Personaje {request.id_personaje_1} no encontrado")
    if not p2:
        raise HTTPException(status_code=404, detail=f"Personaje {request.id_personaje_2} no encontrado")
    if p1.id == p2.id:
        raise HTTPException(status_code=400, detail="Un personaje no puede batallar contra sí mismo")

    return simular_batalla(p1, p2)
