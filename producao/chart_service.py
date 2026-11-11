import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .config import CORES_TIPO, COR_POLITICA, ROTULO


class ChartMixin:
    def pintar_tabela(self, dados, titulo, caminho, fontsize=9):
        fig_h = 0.48 * len(dados) + 1.2
        fig, ax = plt.subplots(figsize=(max(12, 1.4 * max(len(r) for r in dados)), fig_h))
        ax.axis("off")
        tabela = ax.table(cellText=dados, loc="center", cellLoc="center")
        tabela.auto_set_font_size(False)
        tabela.set_fontsize(fontsize)
        tabela.scale(1.05, 1.45)
        for (i, _), cell in tabela.get_celld().items():
            cell.set_edgecolor("#cccccc")
            if i == 0:
                cell.set_facecolor("#1f4e78")
                cell.set_text_props(color="white", fontweight="bold")
            else:
                cell.set_facecolor("#f7f7f7" if i % 2 == 0 else "#ffffff")
        ax.set_title(titulo, fontsize=12, fontweight="bold", pad=12)
        plt.tight_layout()
        plt.savefig(caminho, dpi=200, bbox_inches="tight")
        plt.close()

    def grafico_ociosidade(self, analises, pasta, nome_rodada):
        base = analises["Proposta"]["df_analise"]
        fig, ax = plt.subplots(figsize=(13, 6))
        x = np.arange(len(base))
        width = 0.18
        ax.bar(x - 1.5 * width, base["Effective Workload (min)"], width, label="Proposed workload", color="#1f4e78")
        series = [
            ("Proposta", "Internal Idle Time (min)", -0.5, "Proposed idle"),
            ("FIFO_linha", "Internal Idle Time (min)", 0.5, "FIFO line idle"),
            ("FIFO_maquina", "Internal Idle Time (min)", 1.5, "FIFO machine idle"),
        ]
        for chave, col, desloc, rotulo in series:
            ref = analises[chave]["df_analise"].set_index("Machine")
            valores = ref.reindex(base["Machine"])[col].fillna(0.0)
            ax.bar(x + desloc * width, valores, width, label=rotulo, color=COR_POLITICA[chave], alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(base["Machine"], rotation=30, ha="right")
        ax.set_ylabel("Minutes")
        ax.set_title(f"Workload and internal idle time ({nome_rodada})")
        ax.legend(ncol=2, fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, f"bottlenecks_idle_time_analysis_{nome_rodada.lower()}.png"), dpi=200)
        plt.close()

    def grafico_setup(self, analises, pasta, nome_rodada):
        base = analises["Proposta"]["df_analise"]
        fig, ax = plt.subplots(figsize=(13, 6))
        x = np.arange(len(base))
        width = 0.25
        for i, chave in enumerate(("Proposta", "FIFO_linha", "FIFO_maquina")):
            ref = analises[chave]["df_analise"].set_index("Machine")
            valores = ref.reindex(base["Machine"])["Setup Time (min)"].fillna(0.0)
            ax.bar(x + (i - 1) * width, valores, width, label=ROTULO[chave], color=COR_POLITICA[chave])
        ax.set_xticks(x)
        ax.set_xticklabels(base["Machine"], rotation=30, ha="right")
        ax.set_ylabel("Setup minutes")
        ax.set_title(f"Setup time by machine ({nome_rodada})")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, f"setup_comparison_{nome_rodada.lower()}.png"), dpi=200)
        plt.close()

    def grafico_acumulado(self, resultados, pasta, nome_rodada, cap):
        fig, ax = plt.subplots(figsize=(10, 5))
        for chave in ("FIFO_linha", "FIFO_maquina", "Proposta"):
            fins = np.sort(np.array(resultados[chave]["job_end"], dtype=float))
            ax.step(fins / cap, np.arange(1, len(fins) + 1), where="post",
                    label=ROTULO[chave], color=COR_POLITICA[chave], linewidth=2)
        ax.set_xlabel("Working days from the first release")
        ax.set_ylabel("Parts completed")
        ax.set_title(f"Cumulative completions ({nome_rodada})")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, f"cumulative_completions_{nome_rodada.lower()}.png"), dpi=200)
        plt.close()

    def grafico_gantt_amostra(self, df_gantt, maquinas, pasta, nome, arquivo, cap, dias=5):
        horizonte = cap * dias
        fig_h = max(4.5, 0.38 * len(maquinas) + 1.5)
        fig, ax = plt.subplots(figsize=(14, fig_h))
        y = {maq["id"]: i for i, maq in enumerate(maquinas)}
        amostra = df_gantt[df_gantt["Start_Setup_Min"] < horizonte]
        for _, op in amostra.iterrows():
            cor = CORES_TIPO.get(op["Type"], "#444444")
            ax.barh(y[op["Mach_Idx"]], op["Duration_Proc"], left=op["Start_Proc_Min"] / 60.0,
                    height=0.62, color=cor, edgecolor="none")
            if op["Duration_Setup"] > 0:
                ax.barh(y[op["Mach_Idx"]], op["Duration_Setup"], left=op["Start_Setup_Min"] / 60.0,
                        height=0.62, color="#222222", alpha=0.8)
        for d in range(dias + 1):
            ax.axvline(d * cap / 60.0, color="#bbbbbb", linewidth=0.6)
        ax.set_yticks(range(len(maquinas)))
        ax.set_yticklabels([maq["nome"] for maq in maquinas], fontsize=8)
        ax.set_xlabel(f"Working hours (first {dias} working days). Black is setup.")
        ax.set_title(nome)
        handles = [plt.Rectangle((0, 0), 1, 1, color=CORES_TIPO[t]) for t in sorted(CORES_TIPO)]
        ax.legend(handles, sorted(CORES_TIPO), ncol=10, fontsize=8, loc="upper right")
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, arquivo), dpi=160)
        plt.close()

    def grafico_gantt_gargalo(self, analises, maquinas, pasta, nome_rodada, cap, dias=8):
        info = self.gargalo_de(analises["Proposta"]["df_analise"])
        if info is None:
            return
        tipo = info["machine_type"]
        ids = [maq["id"] for maq in maquinas if maq["tipo"] == tipo - 1]
        horizonte = cap * dias
        fig, eixos = plt.subplots(len(ids), 1, figsize=(13, 2.6 * len(ids)), sharex=True)
        if len(ids) == 1:
            eixos = [eixos]
        for ax, m_idx in zip(eixos, ids):
            nome = maquinas[m_idx]["nome"]
            faixa = {"FIFO_linha": 2, "FIFO_maquina": 1, "Proposta": 0}
            for chave, y in faixa.items():
                df = analises[chave]["df_gantt"]
                sub = df[(df["Mach_Idx"] == m_idx) & (df["Start_Setup_Min"] < horizonte)]
                for _, op in sub.iterrows():
                    ax.barh(y, op["Duration_Proc"] / 60.0, left=op["Start_Proc_Min"] / 60.0,
                            height=0.7, color=CORES_TIPO.get(op["Type"], "#444"), edgecolor="none")
                    if op["Duration_Setup"]:
                        ax.barh(y, op["Duration_Setup"] / 60.0, left=op["Start_Setup_Min"] / 60.0,
                                height=0.7, color="#222", alpha=0.85)
            ax.set_yticks([0, 1, 2])
            ax.set_yticklabels(["Proposed", "FIFO machine", "FIFO line"])
            ax.set_title(f"{nome} — bottleneck of {nome_rodada}")
            ax.grid(axis="x", linestyle="--", alpha=0.4)
        eixos[-1].set_xlabel(f"Working hours (first {dias} days). Black bars are setups; color is part type.")
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, f"gantt_bottleneck_{nome_rodada.lower()}.png"), dpi=160)
        plt.close()

    def graficos_consolidados(self, resultados, pasta):
        rodadas = [r["rodada"] for r in resultados]
        x = np.arange(len(rodadas))
        width = 0.25

        fig, ax = plt.subplots(figsize=(10, 5))
        for i, chave in enumerate(("Proposta", "FIFO_linha", "FIFO_maquina")):
            vals = [r["analises"][chave]["media_tempo_producao"] for r in resultados]
            ax.bar(x + (i - 1) * width, vals, width, label=ROTULO[chave], color=COR_POLITICA[chave])
        ax.axhline(self.config.deadline_days, color="black", linestyle=":", label=f"Deadline ({self.config.deadline_days} calendar days)")
        ax.set_xticks(x)
        ax.set_xticklabels(rodadas)
        ax.set_ylabel("Mean lead time (calendar days)")
        ax.set_title("Lead time on the real order book")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, "lead_time_by_round.png"), dpi=200)
        plt.close()

        fig, ax = plt.subplots(figsize=(10, 5))
        for i, chave in enumerate(("Proposta", "FIFO_linha", "FIFO_maquina")):
            vals = [r["analises"][chave]["total_atrasadas"] for r in resultados]
            ax.bar(x + (i - 1) * width, vals, width, label=ROTULO[chave], color=COR_POLITICA[chave])
        ax.set_xticks(x)
        ax.set_xticklabels(rodadas)
        ax.set_ylabel("Delayed parts")
        ax.set_title("Orders finishing after the 20-day calendar deadline")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, "delayed_parts_by_round.png"), dpi=200)
        plt.close()

        fig, ax = plt.subplots(figsize=(10, 5))
        for i, chave in enumerate(("Proposta", "FIFO_linha", "FIFO_maquina")):
            vals = [r["analises"][chave]["setup_total"] / 60.0 for r in resultados]
            ax.bar(x + (i - 1) * width, vals, width, label=ROTULO[chave], color=COR_POLITICA[chave])
        ax.set_xticks(x)
        ax.set_xticklabels(rodadas)
        ax.set_ylabel("Setup hours")
        ax.set_title("Total setup hours")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, "setup_hours_by_round.png"), dpi=200)
        plt.close()

        if resultados and len(resultados[0]["prop_arr"]):
            n_rodadas = len(resultados)
            altura = min(12, 6 + 0.35 * max(0, n_rodadas - 4))
            largura = min(16, 11 + 0.2 * max(0, n_rodadas - 6))
            fig, ax = plt.subplots(figsize=(largura, altura))
            cores = plt.get_cmap("tab10")(np.linspace(0, 1, len(resultados)))
            for i, r in enumerate(resultados):
                cor = cores[i]
                xs = np.arange(1, len(r["prop_arr"]) + 1)
                ax.plot(xs, r["prop_arr"], marker="o", color=cor, label=f"Proposed {r['rodada']}")
                ax.plot(xs, r["linha_arr"], marker="x", color=cor, linestyle="--", alpha=0.75,
                        label=f"FIFO line {r['rodada']}")
            valores = np.concatenate([
                np.asarray(r[chave], dtype=float).ravel()
                for r in resultados for chave in ("prop_arr", "linha_arr")
            ])
            valores = valores[np.isfinite(valores)]
            if valores.size:
                minimo, maximo = float(valores.min()), float(valores.max())
                margem = max((maximo - minimo) * 0.08, 0.5)
                ax.set_ylim(minimo - margem, maximo + margem)
            ax.axhline(self.config.deadline_days, color="black", linestyle=":", label="Deadline (20 days)")
            ax.set_xlabel("Shuffled daily mix")
            ax.set_ylabel("Mean lead time (calendar days)")
            ax.set_title("Same fleet, daily mix shuffled inside each arrival day")
            ax.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()
            fig.savefig(os.path.join(pasta, "plant_stress_curve_consolidated.png"), dpi=300, bbox_inches="tight")
            plt.close()

            fig, ax = plt.subplots(figsize=(8, 5))
            dados = [r["prop_arr"] for r in resultados]
            bp = ax.boxplot(dados, patch_artist=True, widths=0.5)
            for patch, cor in zip(bp["boxes"], cores):
                patch.set_facecolor(cor)
                patch.set_alpha(0.8)
            ax.set_xticklabels(rodadas)
            ax.set_ylabel("Mean lead time (calendar days)")
            ax.set_title("Proposed policy across shuffled daily mixes")
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            fig.tight_layout()
            fig.savefig(os.path.join(pasta, "instances_distribution_boxplot_consolidated.png"), dpi=200)
            plt.close()

        dados = [["Round", "Proposed lead time", "FIFO line", "FIFO machine",
                  "Delayed proposed", "Delayed FIFO line", "Delayed FIFO machine",
                  "Gain vs line", "Bottleneck", "Rule"]]
        for r in resultados:
            ap, al, am = r["analises"]["Proposta"], r["analises"]["FIFO_linha"], r["analises"]["FIFO_maquina"]
            dados.append([
                r["rodada"], f"{ap['media_tempo_producao']:.2f} d", f"{al['media_tempo_producao']:.2f} d",
                f"{am['media_tempo_producao']:.2f} d", str(ap["total_atrasadas"]), str(al["total_atrasadas"]),
                str(am["total_atrasadas"]), f"{r['ganho_linha']:.1f}%",
                f"Machine {r['gargalo']} ({r['gargalo_util']:.0f}%)", r["regra"],
            ])
        self.pintar_tabela(
            dados,
            f"{len(resultados)} rounds on the real order book",
            os.path.join(pasta, "statistical_results_table_consolidated.png"),
            8,
        )
