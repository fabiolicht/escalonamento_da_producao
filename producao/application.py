from .analysis_service import AnalysisMixin
from .calendar_service import CalendarMixin
from .chart_service import ChartMixin
from .data_service import DataMixin
from .report_service import ReportMixin
from .simulation_service import SimulationMixin


class ProductionApplication(
    CalendarMixin,
    DataMixin,
    AnalysisMixin,
    SimulationMixin,
    ChartMixin,
    ReportMixin,
):
    def __init__(self, config):
        self.config = config

    def run(self):
        self.verificar_calendario()
        selected_rounds = self.config.selected_rounds
        rounds_to_report = (
            set(range(1, self.config.number_of_rounds + 1))
            if selected_rounds is None else set(selected_rounds)
        )
        if not rounds_to_report or min(rounds_to_report) < 1:
            raise ValueError("Round numbers must be positive integers.")

        shift_segments = self.config.shifts[self.config.default_shift]
        results = []
        fleet = None
        added_machine = None
        for number in range(1, max(rounds_to_report) + 1):
            result = self.executar_rodada(
                fleet,
                f"Round_{number}",
                shift_segments,
                self.config.instances,
                self.config.generations,
                self.config.population,
                maquina_adicionada=added_machine,
            )
            if result is None:
                break
            if number in rounds_to_report:
                results.append(result)
            added_machine = result["gargalo"]
            fleet = self.aumentar_frota_no_gargalo(result["qtd"], result["gargalo"])

        if not results:
            print("Nenhuma rodada executada.")
            return
        self.consolidar(
            results,
            shift_segments,
            com_frota=not self.config.skip_fleet_scenarios,
        )
