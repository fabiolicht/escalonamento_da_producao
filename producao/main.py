import argparse
from pathlib import Path

from .application import ProductionApplication
from .config import AppConfig, INSTANCIAS, NUM_RODADAS


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Escalonador FIFO linha, FIFO máquina e política proposta"
    )
    parser.add_argument(
        "--rodadas",
        default=None,
        help="Rodadas a incluir no consolidado, ex.: 1,3; executa também as anteriores necessárias",
    )
    parser.add_argument(
        "--instancias",
        type=int,
        default=INSTANCIAS,
        help="Mixes diários embaralhados para o teste pareado",
    )
    parser.add_argument("--geracoes", type=int, default=3, help="Gerações da busca do ATCS")
    parser.add_argument("--populacao", type=int, default=5, help="Indivíduos por geração")
    parser.add_argument(
        "--sem-frota",
        action="store_true",
        help="Não simula compra de máquinas nem turnos extras",
    )
    args = parser.parse_args(argv)

    try:
        selected_rounds = (
            None if args.rodadas is None
            else frozenset(int(value) for value in args.rodadas.split(",") if value.strip())
        )
    except ValueError:
        parser.error("--rodadas deve conter números inteiros positivos")
    if selected_rounds is not None and (not selected_rounds or min(selected_rounds) < 1):
        parser.error("--rodadas deve conter números inteiros positivos")

    config = AppConfig(
        base_dir=Path(__file__).resolve().parent.parent,
        number_of_rounds=NUM_RODADAS,
        instances=args.instancias,
        generations=args.geracoes,
        population=args.populacao,
        skip_fleet_scenarios=args.sem_frota,
        selected_rounds=selected_rounds,
    )
    ProductionApplication(config).run()


if __name__ == "__main__":
    main()
