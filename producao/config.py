from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

DEADLINE_DIAS = 20
NUM_RODADAS = 5
INSTANCIAS = 5
TURNOS = {
    "1_turno": [(8 * 60, 12 * 60), (13 * 60, 17 * 60)],
    "hora_extra": [(8 * 60, 12 * 60), (13 * 60, 19 * 60)],
    "dois_turnos": [(8 * 60, 12 * 60), (13 * 60, 17 * 60), (18 * 60, 22 * 60), (23 * 60, 27 * 60)],
}
NOME_TURNO = {
    "1_turno": "One shift (8 h, lunch 12:00-13:00)",
    "hora_extra": "One shift + 2 h overtime (10 h)",
    "dois_turnos": "Two shifts (16 h)",
}
TURNO_PADRAO = "1_turno"
CORES_TIPO = {
    "A": "#1f77b4", "B": "#ff7f0e", "C": "#2ca02c", "D": "#d62728", "E": "#9467bd",
    "F": "#8c564b", "G": "#e377c2", "H": "#7f7f7f", "I": "#bcbd22", "J": "#17becf",
}
COR_POLITICA = {
    "FIFO_linha": "#e07a3d",
    "FIFO_maquina": "#c0392b",
    "Proposta": "#1f4e78",
}
ROTULO = {
    "FIFO_linha": "FIFO line",
    "FIFO_maquina": "FIFO per machine",
    "Proposta": "Proposed",
}


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    deadline_days: int = DEADLINE_DIAS
    number_of_rounds: int = NUM_RODADAS
    instances: int = INSTANCIAS
    generations: int = 3
    population: int = 5
    skip_fleet_scenarios: bool = False
    selected_rounds: Optional[FrozenSet[int]] = None
    default_shift: str = TURNO_PADRAO
    shifts: Dict[str, List[Tuple[int, int]]] = field(default_factory=lambda: {
        name: list(periods) for name, periods in TURNOS.items()
    })
    shift_names: Dict[str, str] = field(default_factory=lambda: NOME_TURNO.copy())
