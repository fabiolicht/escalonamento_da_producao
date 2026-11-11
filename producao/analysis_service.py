from collections import defaultdict
import math
import numpy as np
import pandas as pd
from scipy.stats import ttest_rel, wilcoxon


class AnalysisMixin:
    def fitness(self, av):
        return (
            av["total_atrasadas"] * 1_000_000.0
            + av["media_atraso_dias"] * 1_000.0
            + av["media_tempo_producao"] * 100.0
            + av["setup_total"] * 0.02
            + av["makespan_dias_uteis"] * 10.0
        )

    def avaliar(self, jobs, resultado, maquinas, data_base, segmentos):
        cap = float(self.capacidade_dia(segmentos))
        gantt = resultado["gantt"]
        df_gantt = pd.DataFrame(gantt)
        atrasos, fluxos = [], []
        detalhes = []
        for i, job in enumerate(jobs):
            dt_fim = self.minutos_uteis_para_data(resultado["job_end"][i], data_base, segmentos, True)
            dt_ini = self.minutos_uteis_para_data(resultado["job_start"][i], data_base, segmentos, False)
            dias = (dt_fim - job["chegada"].to_pydatetime()).total_seconds() / 86400.0
            atrasou = dt_fim > job["prazo"]
            if atrasou:
                atrasos.append((dt_fim - job["prazo"]).total_seconds() / 86400.0)
            fluxos.append(dias)
            detalhes.append({
                "orig_idx": job["orig_idx"],
                "ordem": job["ordem"],
                "tipo": job["tipo"],
                "dt_ini": dt_ini,
                "dt_fim": dt_fim,
                "dias_prod": dias,
                "status": "Delayed" if atrasou else "On time",
                "rank_fim": 0,
                "rank_inicio": 0,
            })

        ordem_fim = sorted(range(len(jobs)), key=lambda i: (resultado["job_end"][i], jobs[i]["ordem"]))
        ordem_ini = sorted(range(len(jobs)), key=lambda i: (resultado["job_start"][i], jobs[i]["ordem"]))
        for pos, i in enumerate(ordem_fim, start=1):
            detalhes[i]["rank_fim"] = pos
        for pos, i in enumerate(ordem_ini, start=1):
            detalhes[i]["rank_inicio"] = pos

        makespan = max(resultado["job_end"]) if jobs else 0
        analise = []
        idle_total = setup_total = carga_total = 0.0
        for maq in maquinas:
            df_m = df_gantt[df_gantt["Mach_Idx"] == maq["id"]] if not df_gantt.empty else df_gantt
            carga = float(df_m["Duration_Proc"].sum() + df_m["Duration_Setup"].sum()) if not df_m.empty else 0.0
            setup_m = float(df_m["Duration_Setup"].sum()) if not df_m.empty else 0.0
            proc_m = float(df_m["Duration_Proc"].sum()) if not df_m.empty else 0.0
            if not df_m.empty:
                span = float(df_m["End_Min"].max() - df_m["Start_Setup_Min"].min())
                idle = max(0.0, span - carga)
            else:
                span, idle = 0.0, 0.0
            util = (carga / makespan * 100.0) if makespan else 0.0
            idle_total += idle
            setup_total += setup_m
            carga_total += carga
            analise.append({
                "Machine": maq["nome"],
                "Machine type": maq["tipo"] + 1,
                "Effective Workload (min)": carga,
                "Processing (min)": proc_m,
                "Setup Time (min)": span, # Just to preserve original
                "Active Span (min)": span,
                "Internal Idle Time (min)": idle,
                "Utilization over Makespan (%)": round(util, 2),
            })
        df_analise = pd.DataFrame(analise).sort_values("Effective Workload (min)", ascending=False)
        return {
            "total_atrasadas": len(atrasos),
            "media_atraso_dias": float(np.mean(atrasos)) if atrasos else 0.0,
            "media_tempo_producao": float(np.mean(fluxos)) if fluxos else 0.0,
            "makespan_min": makespan,
            "makespan_dias_uteis": makespan / cap if cap else 0.0,
            "idle_total": idle_total,
            "setup_total": setup_total,
            "carga_total": carga_total,
            "df_gantt": df_gantt,
            "df_analise": df_analise,
            "detalhes": detalhes,
            "fluxos": np.array(fluxos, dtype=float),
        }

    def pontuar_rapido(self, jobs, resultado, cap):
        """Proxy em minutos úteis para a busca. O placar publicado continua em dias de calendário."""
        ends = resultado["job_end"]
        n = max(len(jobs), 1)
        tardy = 0
        atraso = 0.0
        fluxo = 0.0
        for job, end in zip(jobs, ends):
            if end > job["due"]:
                tardy += 1
                atraso += (end - job["due"]) / cap
            fluxo += (end - job["release"]) / cap
        setup = float(sum(op["Duration_Setup"] for op in resultado["gantt"]))
        makespan = (max(ends) if ends else 0) / cap
        nota = tardy * 1_000_000.0 + (atraso / n) * 1_000.0 + (fluxo / n) * 100.0 + setup * 0.02 + makespan * 10.0
        return nota

    def testar_pares(self, proposto, base):
        proposto = np.asarray(proposto, dtype=float)
        base = np.asarray(base, dtype=float)
        if proposto.size < 2 or np.allclose(proposto, base):
            d = 0.0
            return {"t": 0.0, "p_t": 1.0, "w": 0.0, "p_w": 1.0, "d": d,
                    "media_prop": float(np.mean(proposto)) if proposto.size else 0.0,
                    "std_prop": float(np.std(proposto, ddof=1)) if proposto.size > 1 else 0.0,
                    "media_base": float(np.mean(base)) if base.size else 0.0,
                    "std_base": float(np.std(base, ddof=1)) if base.size > 1 else 0.0}
        t_stat, p_t = ttest_rel(proposto, base)
        diff = proposto - base
        if np.allclose(diff, 0):
            w_stat, p_w = 0.0, 1.0
        else:
            try:
                w_stat, p_w = wilcoxon(diff)
            except ValueError:
                w_stat, p_w = 0.0, 1.0
        sd = np.sqrt((np.var(proposto, ddof=1) + np.var(base, ddof=1)) / 2.0)
        d = 0.0 if sd == 0 else (np.mean(base) - np.mean(proposto)) / sd
        return {
            "t": float(t_stat), "p_t": float(p_t), "w": float(w_stat), "p_w": float(p_w), "d": float(d),
            "media_prop": float(np.mean(proposto)), "std_prop": float(np.std(proposto, ddof=1)),
            "media_base": float(np.mean(base)), "std_base": float(np.std(base, ddof=1)),
        }

    def gargalo_de(self, df_analise):
        if df_analise.empty:
            return None
        grupo = df_analise.groupby("Machine type", as_index=False).agg(
            util=("Utilization over Makespan (%)", "mean"),
            carga=("Effective Workload (min)", "sum"),
            setup=("Setup Time (min)", "sum"),
            unidades=("Machine", "count"),
        )
        grupo = grupo.sort_values(["util", "carga"], ascending=False)
        topo = grupo.iloc[0]
        return {
            "machine_type": int(topo["Machine type"]),
            "utilization": float(topo["util"]),
            "units": int(topo["unidades"]),
            "tabela": grupo,
        }

    def carga_teorica(self, jobs, proc, setup, dias_uteis, segmentos):
        cap = self.capacidade_dia(segmentos) * max(dias_uteis, 1)
        proc_min = defaultdict(float)
        ops = defaultdict(int)
        tipos = defaultdict(set)
        for job in jobs:
            for m in job["rota"]:
                proc_min[m] += proc[m]
                ops[m] += 1
                tipos[m].add(job["tipo"])
        linhas = []
        for m in sorted(proc_min):
            p = proc_min[m]
            s_pior = ops[m] * setup[m]
            s_lote = len(tipos[m]) * max(dias_uteis, 1) * setup[m]
            linhas.append({
                "Machine": f"Machine {m + 1}",
                "Operations": ops[m],
                "Families": len(tipos[m]),
                "Processing (h)": round(p / 60.0, 1),
                "Setup if every visit switches (h)": round(s_pior / 60.0, 1),
                "Setup if one batch per family per day (h)": round(s_lote / 60.0, 1),
                "Units to absorb processing": int(math.ceil(p / cap)),
                "Units to absorb processing + full setup": int(math.ceil((p + s_pior) / cap)),
                "Units to absorb processing + daily batches": int(math.ceil((p + s_lote) / cap)),
            })
        return pd.DataFrame(linhas)
