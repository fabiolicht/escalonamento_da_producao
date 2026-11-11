import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .config import CORES_TIPO, ROTULO


class ReportMixin:
    def montar_gantt_export(self, resultado, jobs, data_base, segmentos, politica):
        df = resultado["df_gantt"].copy()
        df["Policy"] = politica
        df["Part"] = [f"P{int(i) + 1}" for i in df["orig_idx"]]
        df["Start"] = [self.minutos_uteis_para_data(v, data_base, segmentos, False) for v in df["Start_Setup_Min"]]
        df["Process start"] = [self.minutos_uteis_para_data(v, data_base, segmentos, False) for v in df["Start_Proc_Min"]]
        df["End"] = [self.minutos_uteis_para_data(v, data_base, segmentos, True) for v in df["End_Min"]]
        df = df.sort_values(["Start_Setup_Min", "Mach_Idx", "Part_Idx"])
        df["Production sequence"] = np.arange(1, len(df) + 1)
        cols = ["Policy", "Production sequence", "Part", "Type", "Op", "Machine",
                "Start", "Process start", "End", "Duration_Setup", "Duration_Proc",
                "Start_Setup_Min", "End_Min"]
        return df[cols]

    def preencher_entrada(self, df_entrada, jobs, analises):
        df = df_entrada.copy()
        df["Data Saída"] = pd.NaT
        df["Tempo de produção (dias)"] = np.nan
        df["Status"] = pd.Series([pd.NA] * len(df), dtype="object")
        mapas = {
            "Proposta": ("Data Saída", "Tempo de produção (dias)", "Status",
                         "Ordem de conclusão (proposta)", "Ordem de entrada na linha (proposta)"),
            "FIFO_linha": ("Data Saída FIFO linha", "Tempo FIFO linha (dias)", "Status FIFO linha",
                           "Ordem de conclusão (FIFO linha)", "Ordem de entrada na linha (FIFO linha)"),
            "FIFO_maquina": ("Data Saída FIFO máquina", "Tempo FIFO máquina (dias)", "Status FIFO máquina",
                             "Ordem de conclusão (FIFO máquina)", "Ordem de entrada na linha (FIFO máquina)"),
        }
        for chave, (c_fim, c_dias, c_status, c_rank_f, c_rank_i) in mapas.items():
            if c_fim not in df.columns:
                df[c_fim] = pd.Series([pd.NA] * len(df), dtype="object")
            df[c_dias] = np.nan
            df[c_status] = pd.Series([pd.NA] * len(df), dtype="object")
            df[c_rank_f] = np.nan
            df[c_rank_i] = np.nan
            for det in analises[chave]["detalhes"]:
                idx = det["orig_idx"]
                df.at[idx, c_fim] = det["dt_fim"]
                df.at[idx, c_dias] = round(det["dias_prod"], 2)
                df.at[idx, c_status] = det["status"]
                df.at[idx, c_rank_f] = det["rank_fim"]
                df.at[idx, c_rank_i] = det["rank_inicio"]
        return df

    def tabela_ordem(self, jobs, analises):
        n = len(jobs)
        por_rank = {chave: [None] * n for chave in analises}
        for chave, av in analises.items():
            for det in av["detalhes"]:
                por_rank[chave][det["rank_fim"] - 1] = det
        linhas = []
        for pos in range(n):
            linha = {"Completion rank": pos + 1}
            for chave, rotulo in ROTULO.items():
                det = por_rank[chave][pos]
                job = jobs[det["ordem"]]
                linha[f"{rotulo} part"] = f"P{int(det['orig_idx']) + 1}"
                linha[f"{rotulo} type"] = det["tipo"]
                linha[f"{rotulo} end"] = det["dt_fim"]
                linha[f"{rotulo} lead time (d)"] = round(det["dias_prod"], 2)
                linha[f"{rotulo} status"] = det["status"]
                _ = job
            linhas.append(linha)
        return pd.DataFrame(linhas)

    def resumo_politicas(self, analises, regra, params):
        linhas = []
        for chave in ("FIFO_linha", "FIFO_maquina", "Proposta"):
            av = analises[chave]
            linhas.append({
                "Policy": ROTULO[chave],
                "Dispatch rule": regra if chave == "Proposta" else chave,
                "Mean lead time (calendar days)": round(av["media_tempo_producao"], 3),
                "Delayed parts": av["total_atrasadas"],
                "Mean delay of late parts (days)": round(av["media_atraso_dias"], 3),
                "Makespan (working days)": round(av["makespan_dias_uteis"], 2),
                "Setup (min)": round(av["setup_total"], 1),
                "Internal idle (min)": round(av["idle_total"], 1),
                "Parameters": str(params) if chave == "Proposta" else "",
            })
        return pd.DataFrame(linhas)

    def gerar_sequencia_e_gantt_diario(self, analises, maquinas, data_base, segmentos, pasta, nome_rodada):
        import matplotlib.dates as mdates
        import pandas as pd
        import matplotlib.pyplot as plt
        import os

        caminho_xl = os.path.join(pasta, f"sequencia_producao_{nome_rodada.lower()}.xlsx")
        with pd.ExcelWriter(caminho_xl, engine="openpyxl") as writer:
            for chave, label in [("FIFO_linha", "FIFO line"), ("FIFO_maquina", "FIFO per machine"), ("Proposta", "Proposed")]:
                if chave not in analises or analises[chave]["df_gantt"].empty: 
                    continue
                df = analises[chave]["df_gantt"].copy()
                df = df.sort_values(["Start_Setup_Min", "Mach_Idx"])

                seq_df = pd.DataFrame()
                seq_df["Part"] = ["P" + str(int(idx) + 1) for idx in df["orig_idx"]]
                seq_df["Type"] = df["Type"]
                seq_df["Machine"] = [maquinas[m]["nome"] for m in df["Mach_Idx"]]

                dt_start = [self.minutos_uteis_para_data(v, data_base, segmentos, False) for v in df["Start_Setup_Min"]]
                dt_end = [self.minutos_uteis_para_data(v, data_base, segmentos, True) for v in df["End_Min"]]
                dt_proc_start = [self.minutos_uteis_para_data(v, data_base, segmentos, False) for v in df["Start_Proc_Min"]]

                seq_df["Start"] = [d.strftime("%d/%m/%Y %H:%M") for d in dt_start]
                seq_df["End"] = [d.strftime("%d/%m/%Y %H:%M") for d in dt_end]
                seq_df["Processing Duration"] = df["Duration_Proc"]
                seq_df["Setup (min)"] = df["Duration_Setup"]

                seq_df.to_excel(writer, sheet_name=label.replace(" ", "_")[:31], index=False)

                df["dt_start"] = dt_start
                df["dt_end"] = dt_end
                df["dt_proc_start"] = dt_proc_start

                for d in range(1, 4):
                    dia_alvo = self.avancar_dias_uteis(data_base, d - 1)
                    inicio_dia = dia_alvo.replace(hour=8, minute=0, second=0)
                    fim_dia = dia_alvo.replace(hour=17, minute=0, second=0)

                    df_dia = df[(df["dt_start"] < fim_dia) & (df["dt_end"] > inicio_dia)]

                    if df_dia.empty:
                        continue

                    fig, ax = plt.subplots(figsize=(14, max(5, 0.4 * len(maquinas))))
                    y_pos = {maq["id"]: i for i, maq in enumerate(maquinas)}

                    for _, op in df_dia.iterrows():
                        m_idx = op["Mach_Idx"]
                        y = y_pos[m_idx]

                        if op["Duration_Setup"] > 0:
                            s_start = max(inicio_dia, op["dt_start"])
                            s_end = min(fim_dia, op["dt_proc_start"])
                            if s_end > s_start:
                                ax.barh(y, mdates.date2num(s_end) - mdates.date2num(s_start), 
                                        left=mdates.date2num(s_start),
                                        height=0.6, color="white", edgecolor="gray", hatch="///", alpha=0.5, linestyle="--")

                        p_start = max(inicio_dia, op["dt_proc_start"])
                        p_end = min(fim_dia, op["dt_end"])
                        if p_end > p_start:
                            cor = CORES_TIPO.get(op["Type"], "#444444")
                            width = mdates.date2num(p_end) - mdates.date2num(p_start)
                            ax.barh(y, width, left=mdates.date2num(p_start),
                                    height=0.6, color=cor, edgecolor="black", linewidth=0.5, alpha=0.6)

                            cx = mdates.date2num(p_start) + width / 2
                            rotulo = f"{int(op['orig_idx'])+1}{op['Type']}"
                            ax.text(cx, y, rotulo, ha='center', va='center', fontsize=8, color='black', fontweight='bold')

                    ax.set_yticks(range(len(maquinas)))
                    ax.set_yticklabels([maq["nome"] for maq in maquinas])
                    ax.set_xlim(mdates.date2num(inicio_dia), mdates.date2num(fim_dia))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

                    ax.grid(axis="x", linestyle="--", alpha=0.7)
                    ax.set_title(f"Production Daily Schedule - Day {d} ({dia_alvo.strftime('%d/%m/%Y')}) - {label}", pad=15, fontweight="bold")
                    ax.set_xlabel("Working Hours (08:00 - 17:00)", fontweight="bold")

                    fig.tight_layout()
                    caminho_fig = os.path.join(pasta, f"gantt_day_{d}_{label.replace(' ', '_').lower()}_{nome_rodada.lower()}.png")
                    fig.savefig(caminho_fig, dpi=200)
                    plt.close(fig)

    def executar_rodada(self, qtd, nome_rodada, segmentos, n_instancias, n_gen, pop,
                        maquina_adicionada=None):
        pasta = os.path.join(self.config.base_dir, f"Execucao_Rodada_{nome_rodada}")
        os.makedirs(pasta, exist_ok=True)
        print(f"\n--- {nome_rodada} ---")

        df_entrada, df_dados = self.carregar_planilha()
        rotas, proc, setup = self.extrair_rotas_e_tempos(df_dados)
        if qtd is None:
            qtd = {tipo: 1 for tipo in proc}
        else:
            qtd = dict(qtd)
        data_base = self.alinhar_dia_util(df_entrada["Data entrada"].min())
        df_pendentes = df_entrada.copy()
        if df_pendentes.empty:
            print("Nenhuma ordem na planilha.")
            return None

        jobs = self.montar_jobs(df_pendentes, rotas, proc, data_base, segmentos)
        maquinas = self.montar_maquinas(rotas, qtd)
        dias = df_pendentes["Data entrada"].dt.normalize().nunique()
        taxa = float(df_pendentes.groupby(df_pendentes["Data entrada"].dt.date).size().mean())
        cap = self.capacidade_dia(segmentos)
        print(f"  {len(jobs)} ordens | {len(maquinas)} máquinas | {taxa:.2f} peças/dia | turno {cap} min")

        resultados = {}
        analises = {}
        for regra in ("FIFO_LINHA", "FIFO_MAQUINA"):
            print(f"  Simulando {regra}...")
            res = self.simular_linha(jobs, maquinas, proc, setup, regra)
            chave = "FIFO_linha" if regra == "FIFO_LINHA" else "FIFO_maquina"
            resultados[chave] = res
            analises[chave] = self.avaliar(jobs, res, maquinas, data_base, segmentos)
            av = analises[chave]
            print(f"    lead {av['media_tempo_producao']:.2f} d | atrasadas {av['total_atrasadas']} | "
                  f"setup {av['setup_total']:.0f} min | makespan {av['makespan_dias_uteis']:.1f} d úteis")

        regra, params, av_prop, res_prop = self.escolher_politica(
            jobs, maquinas, proc, setup, data_base, segmentos, n_gen, pop, seed=42
        )
        resultados["Proposta"] = res_prop
        analises["Proposta"] = av_prop
        print(f"  Política da rodada: {regra} {params}")
        print(f"    lead {av_prop['media_tempo_producao']:.2f} d | atrasadas {av_prop['total_atrasadas']} | "
              f"setup {av_prop['setup_total']:.0f} min | makespan {av_prop['makespan_dias_uteis']:.1f} d úteis")

        base_linha = analises["FIFO_linha"]["media_tempo_producao"]
        base_maq = analises["FIFO_maquina"]["media_tempo_producao"]
        ganho_linha = 100.0 * (base_linha - av_prop["media_tempo_producao"]) / base_linha if base_linha else 0.0
        ganho_maq = 100.0 * (base_maq - av_prop["media_tempo_producao"]) / base_maq if base_maq else 0.0
        print(f"  Ganho de lead time: {ganho_linha:.1f}% contra FIFO da linha, {ganho_maq:.1f}% contra FIFO por máquina")

        info_g = self.gargalo_de(av_prop["df_analise"])
        print(f"  Gargalo da proposta: Machine {info_g['machine_type']} "
              f"({info_g['units']} un., utilização média {info_g['utilization']:.1f}%)")
        mudanca_frota = (
            "1 unidade de cada tipo (frota inicial)" if maquina_adicionada is None
            else f"+1 Machine {maquina_adicionada} (gargalo da rodada anterior)"
        )

        print(f"  Perturbando o mix diário ({n_instancias} instâncias)...")
        prop_arr, linha_arr, maq_arr, stats = self.benchmark(
            df_pendentes, rotas, proc, setup, maquinas, data_base, segmentos,
            regra, params, n_instancias, seed=42
        )

        df_saida = self.preencher_entrada(df_entrada, jobs, analises)
        gantts = [self.montar_gantt_export(analises[k], jobs, data_base, segmentos, ROTULO[k])
                  for k in ("FIFO_linha", "FIFO_maquina", "Proposta")]
        df_gantt = pd.concat(gantts, ignore_index=True)
        df_ordem = self.tabela_ordem(jobs, analises)
        df_resumo = self.resumo_politicas(analises, regra, params)
        df_carga = self.carga_teorica(jobs, proc, setup, dias, segmentos)
        qtd_df = pd.DataFrame([{"Machine": f"Machine {m + 1}", "Units in this round": n} for m, n in sorted(qtd.items())])

        caminho_xl = os.path.join(pasta, f"parts_updated_{nome_rodada.lower()}.xlsx")
        with pd.ExcelWriter(caminho_xl, engine="openpyxl") as writer:
            df_saida.to_excel(writer, sheet_name="Entrada", index=False)
            df_dados.to_excel(writer, sheet_name="Dados", index=False)
            df_gantt.to_excel(writer, sheet_name="Gantt", index=False)
            df_ordem.to_excel(writer, sheet_name="Production order", index=False)
            df_resumo.to_excel(writer, sheet_name="Policy comparison", index=False)
            for chave in ("Proposta", "FIFO_linha", "FIFO_maquina"):
                analises[chave]["df_analise"].to_excel(writer, sheet_name=f"Idle {ROTULO[chave]}"[:31], index=False)
            info_g["tabela"].to_excel(writer, sheet_name="Bottleneck", index=False)
            df_carga.to_excel(writer, sheet_name="Capacity requirement", index=False)
            qtd_df.to_excel(writer, sheet_name="Fleet", index=False)

        self.grafico_ociosidade(analises, pasta, nome_rodada)
        self.grafico_setup(analises, pasta, nome_rodada)
        self.grafico_acumulado(resultados, pasta, nome_rodada, cap)
        for chave in ("FIFO_linha", "FIFO_maquina", "Proposta"):
            self.grafico_gantt_amostra(
                analises[chave]["df_gantt"], maquinas, pasta,
                f"{ROTULO[chave]} {nome_rodada}",
                f"gantt_first_5d_{chave.lower()}_{nome_rodada.lower()}.png",
                cap, dias=5,
            )
        self.grafico_gantt_gargalo(analises, maquinas, pasta, nome_rodada, cap, dias=8)

        dados_tab = [[
            "Indicator", "Proposed", "FIFO line", "FIFO per machine", "Gain vs line", "Gain vs machine",
        ]]
        def linha_tab(nome, a, b, c, fmt="{:.2f}"):
            ga = 100.0 * (b - a) / b if b else 0.0
            gb = 100.0 * (c - a) / c if c else 0.0
            return [nome, fmt.format(a), fmt.format(b), fmt.format(c), f"{ga:.1f}%", f"{gb:.1f}%"]

        al, am, ap = analises["FIFO_linha"], analises["FIFO_maquina"], analises["Proposta"]
        dados_tab.append(linha_tab("Mean lead time (days)", ap["media_tempo_producao"], al["media_tempo_producao"], am["media_tempo_producao"]))
        dados_tab.append(linha_tab("Delayed parts", ap["total_atrasadas"], al["total_atrasadas"], am["total_atrasadas"], "{:.0f}"))
        dados_tab.append(linha_tab("Makespan (working days)", ap["makespan_dias_uteis"], al["makespan_dias_uteis"], am["makespan_dias_uteis"]))
        dados_tab.append(linha_tab("Setup (min)", ap["setup_total"], al["setup_total"], am["setup_total"], "{:.0f}"))
        dados_tab.append(["Dispatch rule", regra, "Arrival order", "Queue arrival", "", ""])
        dados_tab.append(["Deadline", f"{self.config.deadline_days} calendar days", self.config.shift_names[self.config.default_shift], f"{len(jobs)} orders", "", ""])
        if stats:
            sl, sm = stats["vs_linha"], stats["vs_maquina"]
            dados_tab.append([
                "Shuffled mixes, mean lead time",
                f"{sl['media_prop']:.2f} ± {sl['std_prop']:.2f}",
                f"{sl['media_base']:.2f} ± {sl['std_base']:.2f}",
                f"{sm['media_base']:.2f} ± {sm['std_base']:.2f}",
                f"t={sl['t']:.2f}, p={sl['p_t']:.2e}, d={sl['d']:.2f}",
                f"t={sm['t']:.2f}, p={sm['p_t']:.2e}, d={sm['d']:.2f}",
            ])
        self.pintar_tabela(
            dados_tab,
            f"Measured lead time, delays and setup ({nome_rodada})",
            os.path.join(pasta, f"statistical_results_table_{nome_rodada.lower()}.png"),
            fontsize=8,
        )

        self.gerar_sequencia_e_gantt_diario(analises, maquinas, data_base, segmentos, pasta, nome_rodada)
        with open(os.path.join(pasta, "resumo.txt"), "w", encoding="utf-8") as fh:
            fh.write(
                f"{nome_rodada}\n"
                f"Regra proposta: {regra} {params}\n"
                f"Lead time (dias corridos): proposta {ap['media_tempo_producao']:.2f} | "
                f"FIFO linha {al['media_tempo_producao']:.2f} | FIFO máquina {am['media_tempo_producao']:.2f}\n"
                f"Ganho: {ganho_linha:.1f}% vs FIFO linha, {ganho_maq:.1f}% vs FIFO máquina\n"
                f"Atrasadas: proposta {ap['total_atrasadas']} | linha {al['total_atrasadas']} | máquina {am['total_atrasadas']}\n"
                f"Setup (min): proposta {ap['setup_total']:.0f} | linha {al['setup_total']:.0f} | máquina {am['setup_total']:.0f}\n"
                f"Gargalo: Machine {info_g['machine_type']} com {info_g['units']} unidade(s), "
                f"utilização {info_g['utilization']:.1f}%\n"
                f"Frota usada: {mudanca_frota}.\n"
                f"Quantidades da aba Dados são ignoradas.\n"
                f"Próxima rodada: adicionar +1 Machine {info_g['machine_type']}.\n"
            )

        return {
            "rodada": nome_rodada,
            "regra": regra,
            "params": params,
            "qtd": dict(qtd),
            "mudanca_frota": mudanca_frota,
            "analises": {k: {
                "media_tempo_producao": v["media_tempo_producao"],
                "total_atrasadas": v["total_atrasadas"],
                "media_atraso_dias": v["media_atraso_dias"],
                "makespan_dias_uteis": v["makespan_dias_uteis"],
                "setup_total": v["setup_total"],
                "idle_total": v["idle_total"],
            } for k, v in analises.items()},
            "gargalo": info_g["machine_type"],
            "gargalo_util": info_g["utilization"],
            "prop_arr": prop_arr,
            "linha_arr": linha_arr,
            "maq_arr": maq_arr,
            "stats": stats,
            "ganho_linha": ganho_linha,
            "ganho_maq": ganho_maq,
            "n_pecas": len(jobs),
            "taxa": taxa,
            "jobs": jobs,
            "rotas": rotas,
            "proc": proc,
            "setup": setup,
            "data_base": data_base,
        }

    def consolidar(self, resultados, segmentos, com_frota):
        pasta = os.path.join(self.config.base_dir, "Execucao_Consolidada")
        os.makedirs(pasta, exist_ok=True)
        self.graficos_consolidados(resultados, pasta)

        primeiro = resultados[0]
        df_entrada, _ = self.carregar_planilha()
        data_base = primeiro["data_base"]
        dias = df_entrada["Data entrada"].dt.normalize().nunique()
        df_carga = self.carga_teorica(primeiro["jobs"], primeiro["proc"], primeiro["setup"], dias, segmentos)

        hist, qtd_alvo = [], {}
        df_turnos = pd.DataFrame()
        if com_frota:
            print("\n--- Compra guiada pelo gargalo, com a política proposta da 1ª rodada ---")
            qtd_alvo, hist, _ = self.projetar_frota(
                primeiro["jobs"], primeiro["rotas"], primeiro["proc"], primeiro["setup"],
                primeiro["qtd"], data_base, segmentos, primeiro["regra"], primeiro["params"], passos=6,
            )
            frotas = []
            for r in resultados:
                frotas.append((r["rodada"].replace("_", " "), r["qtd"]))
            print("--- Turno padrão, hora extra (+2 h) e dois turnos ---")
            df_turnos = self.cenarios_turno(
                df_entrada, primeiro["rotas"], primeiro["proc"], primeiro["setup"],
                frotas, data_base, primeiro["regra"], primeiro["params"],
            )

        linhas = []
        for r in resultados:
            ap, al, am = r["analises"]["Proposta"], r["analises"]["FIFO_linha"], r["analises"]["FIFO_maquina"]
            linhas.append({
                "Round": r["rodada"],
                "Proposed rule": r["regra"],
                "Proposed lead time (days)": round(ap["media_tempo_producao"], 2),
                "FIFO line lead time (days)": round(al["media_tempo_producao"], 2),
                "FIFO machine lead time (days)": round(am["media_tempo_producao"], 2),
                "Gain vs FIFO line (%)": round(r["ganho_linha"], 1),
                "Gain vs FIFO machine (%)": round(r["ganho_maq"], 1),
                "Delayed proposed": ap["total_atrasadas"],
                "Delayed FIFO line": al["total_atrasadas"],
                "Delayed FIFO machine": am["total_atrasadas"],
                "Makespan proposed (working days)": round(ap["makespan_dias_uteis"], 2),
                "Setup proposed (min)": round(ap["setup_total"], 1),
                "Setup FIFO line (min)": round(al["setup_total"], 1),
                "Bottleneck": f"Machine {r['gargalo']}",
                "Bottleneck utilization (%)": round(r["gargalo_util"], 1),
                "Fleet change": r["mudanca_frota"],
                "Parameters": str(r["params"]),
            })

        caminho = os.path.join(pasta, "consolidated_multiround_report.xlsx")
        with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
            pd.DataFrame(linhas).to_excel(writer, sheet_name="Summary", index=False)
            df_carga.to_excel(writer, sheet_name="Capacity requirement", index=False)
            if hist:
                rows = []
                for h in hist:
                    row = {k: v for k, v in h.items() if k != "units"}
                    for tipo, n in sorted(h["units"].items()):
                        row[f"Machine {tipo + 1}"] = n
                    rows.append(row)
                pd.DataFrame(rows).to_excel(writer, sheet_name="Buy bottleneck path", index=False)
                pd.DataFrame([{"Machine": f"Machine {k + 1}", "Units": v} for k, v in sorted(qtd_alvo.items())]).to_excel(
                    writer, sheet_name="Fleet that meets deadline", index=False
                )
            if not df_turnos.empty:
                df_turnos.to_excel(writer, sheet_name="Overtime and shifts", index=False)
            if len(primeiro["prop_arr"]):
                quadro = {"Mix": np.arange(1, len(primeiro["prop_arr"]) + 1)}
                for r in resultados:
                    quadro[f"{r['rodada']} proposed"] = r["prop_arr"]
                    quadro[f"{r['rodada']} FIFO line"] = r["linha_arr"]
                    quadro[f"{r['rodada']} FIFO machine"] = r["maq_arr"]
                pd.DataFrame(quadro).to_excel(writer, sheet_name="Shuffled mixes", index=False)

        if not df_turnos.empty:
            propostas = df_turnos[df_turnos["Policy"] == "Proposed"]
            frotas_u = list(propostas["Fleet"].unique())
            cores_frota = plt.get_cmap("tab10")(np.linspace(0, 1, len(frotas_u)))
            fig, ax = plt.subplots(figsize=(min(16, max(11, 8 + 0.5 * len(frotas_u))), 5))
            for i, frota in enumerate(frotas_u):
                sub = propostas[propostas["Fleet"] == frota]
                ax.plot(
                    sub["Calendar"], sub["Mean lead time (days)"],
                    marker="o", label=frota, color=cores_frota[i],
                )
            ax.axhline(self.config.deadline_days, color="black", linestyle=":", label="Deadline")
            ax.set_ylabel("Mean lead time (calendar days)")
            ax.set_title("Proposed policy under overtime and a second shift")
            ax.tick_params(axis="x", rotation=15)
            ax.legend(
                ncol=min(5, len(frotas_u)),
                fontsize=8,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.2),
            )
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()
            fig.savefig(os.path.join(pasta, "calendar_scenarios_2.png"), dpi=250, bbox_inches="tight")
            plt.close()
            # O gráfico acima esconde a série de atrasos de propósito com alpha 0.
            # A figura que interessa é o lead time; os atrasos ficam na planilha.
            fig, ax = plt.subplots(figsize=(11, 5))
            frotas_u = list(propostas["Fleet"].unique())
            n_frotas = len(frotas_u)
            width = 0.8 / n_frotas
            calendarios = list(propostas["Calendar"].unique())
            x = np.arange(len(calendarios))
            for i, frota in enumerate(frotas_u):
                sub = propostas[propostas["Fleet"] == frota].set_index("Calendar").reindex(calendarios)
                offset = (i - n_frotas / 2 + 0.5) * width
                ax.bar(x + offset, sub["Delayed parts"], width, label=frota)
            ax.set_xticks(x)
            ax.set_xticklabels(calendarios, rotation=15, ha="right")
            ax.set_ylabel("Delayed parts")
            ax.set_title("Deadline misses with overtime or a second shift")
            ax.legend()
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            fig.tight_layout()
            fig.savefig(os.path.join(pasta, "calendar_delayed_parts_2.png"), dpi=200)
            plt.close()

        print(f"\n[OK] Resultados em '{pasta}/'")
