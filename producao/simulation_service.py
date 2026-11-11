import heapq
import math
from collections import defaultdict
import numpy as np
import pandas as pd


class SimulationMixin:
    def simular_linha(self, jobs, maquinas, proc, setup, regra, params=None):
        """Simulação por eventos. Liberação e fim no mesmo instante atualizam as filas juntos."""
        params = params or {}
        n = len(jobs)
        k1 = float(params.get("k1", 1.2))
        k2 = float(params.get("k2", 0.5))
        w_batch = float(params.get("w_batch", 1.4))
        w_wait = float(params.get("w_wait", 0.15))
        pbar = max(1.0, float(np.mean(list(proc.values()))))
        sbar = max(1.0, float(np.mean(list(setup.values()))))

        release = [j["release"] for j in jobs]
        due = [j["due"] for j in jobs]
        rota = [j["rota"] for j in jobs]
        tipo_peca = [j["tipo"] for j in jobs]
        ordem = [j["ordem"] for j in jobs]
        proc_op = [[int(proc[m]) for m in r] for r in rota]
        setup_i = {m: int(setup[m]) for m in setup}

        unidades = defaultdict(list)
        for maq in maquinas:
            unidades[maq["tipo"]].append(maq["id"])
        nome = [maq["nome"] for maq in maquinas]

        op_idx = [0] * n
        pronto = list(release)
        terminou = [False] * n
        restam = [sum(p) for p in proc_op]
        chegou_fila = [0] * n
        inicio_job = [None] * n
        fim_job = [None] * n
        filas = defaultdict(list)
        contagem = defaultdict(lambda: defaultdict(int))

        livre = [0] * len(maquinas)
        ocupada = [False] * len(maquinas)
        ultimo_tipo = [None] * len(maquinas)
        gantt = []
        seq_ev = 0
        pq = []

        def empurrar(t, kind, payload):
            nonlocal seq_ev
            heapq.heappush(pq, (int(t), seq_ev, kind, payload))
            seq_ev += 1

        def enfileirar(i, tipo_maq, agora):
            filas[tipo_maq].append(i)
            contagem[tipo_maq][tipo_peca[i]] += 1
            chegou_fila[i] = agora
            pronto[i] = agora

        def setup_de(i, m_idx, tipo_maq):
            if ultimo_tipo[m_idx] == tipo_peca[i]:
                return 0
            return setup_i[tipo_maq]

        def chave(i, m_idx, tipo_maq, agora):
            su = setup_de(i, m_idx, tipo_maq)
            if regra == "FIFO_LINHA":
                return (ordem[i], su, m_idx)
            if regra == "FIFO_MAQUINA":
                return (chegou_fila[i], ordem[i], su, m_idx)
            if regra == "EDD":
                return (due[i], su, ordem[i], m_idx)
            if regra == "SPT":
                return (proc_op[i][op_idx[i]] + su, su, ordem[i], m_idx)
            if regra == "LOTE":
                mesma = 0 if su == 0 else 1
                irmas = contagem[tipo_maq][tipo_peca[i]]
                return (mesma, -(irmas if su == 0 else 0), due[i], ordem[i], m_idx)
            pr = max(1, proc_op[i][op_idx[i]])
            folga = max(0, due[i] - agora - restam[i])
            atraso = math.exp(-folga / (k1 * pbar))
            troca = math.exp(-su / (k2 * sbar))
            irmas = contagem[tipo_maq][tipo_peca[i]]
            bonus = (1.0 + w_batch * max(0, irmas - 1)) if su == 0 else 1.0
            espera = w_wait * ((agora - chegou_fila[i]) / pbar)
            indice = (1.0 / pr) * atraso * troca * bonus + espera
            return (-indice, due[i], ordem[i], m_idx)

        def iniciar(i, m_idx, agora):
            tipo_maq = rota[i][op_idx[i]]
            su = setup_de(i, m_idx, tipo_maq)
            pr = proc_op[i][op_idx[i]]
            fim = agora + su + pr
            ocupada[m_idx] = True
            livre[m_idx] = fim
            ultimo_tipo[m_idx] = tipo_peca[i]
            filas[tipo_maq].remove(i)
            contagem[tipo_maq][tipo_peca[i]] -= 1
            if inicio_job[i] is None:
                inicio_job[i] = agora
            gantt.append({
                "Part_Idx": i,
                "orig_idx": jobs[i]["orig_idx"],
                "Ordem": ordem[i],
                "Type": tipo_peca[i],
                "Op": op_idx[i],
                "Machine": nome[m_idx],
                "Mach_Idx": m_idx,
                "Tipo_Maq": tipo_maq,
                "Start_Setup_Min": agora,
                "Start_Proc_Min": agora + su,
                "End_Min": fim,
                "Duration_Setup": su,
                "Duration_Proc": pr,
            })
            empurrar(fim, "f", (i, m_idx))

        def despachar(agora):
            while True:
                começou = False
                for tipo_maq, fila in list(filas.items()):
                    if not fila:
                        continue
                    ociosas = [m for m in unidades[tipo_maq] if (not ocupada[m]) and livre[m] <= agora]
                    if not ociosas:
                        continue
                    melhor = None
                    for i in fila:
                        if terminou[i] or pronto[i] > agora:
                            continue
                        for m_idx in ociosas:
                            key = chave(i, m_idx, tipo_maq, agora)
                            if melhor is None or key < melhor[0]:
                                melhor = (key, i, m_idx)
                    if melhor is None:
                        continue
                    _, i, m_idx = melhor
                    iniciar(i, m_idx, agora)
                    começou = True
                    break
                if not começou:
                    return

        for i in range(n):
            empurrar(release[i], "r", i)

        while pq:
            agora = pq[0][0]
            liberacoes, fins = [], []
            while pq and pq[0][0] == agora:
                _, _, kind, payload = heapq.heappop(pq)
                if kind == "r":
                    liberacoes.append(payload)
                else:
                    fins.append(payload)
            for i, m_idx in fins:
                ocupada[m_idx] = False
                tipo_maq = rota[i][op_idx[i]]
                restam[i] -= proc_op[i][op_idx[i]]
                op_idx[i] += 1
                if op_idx[i] >= len(rota[i]):
                    terminou[i] = True
                    fim_job[i] = agora
                else:
                    enfileirar(i, rota[i][op_idx[i]], agora)
                _ = tipo_maq
            for i in liberacoes:
                enfileirar(i, rota[i][0], agora)
            despachar(agora)

        faltam = [i for i, fim in enumerate(fim_job) if fim is None]
        if faltam:
            raise RuntimeError(f"Simulação incompleta: {len(faltam)} peças sem término.")

        return {
            "gantt": gantt,
            "job_start": inicio_job,
            "job_end": fim_job,
            "regra": regra,
            "params": dict(params),
        }

    def otimizar_atcs(self, jobs, maquinas, proc, setup, segmentos, n_gen=4, pop=5, seed=42):
        rng = np.random.default_rng(seed)
        cap = float(self.capacidade_dia(segmentos))
        limites = np.array([
            [0.3, 4.0],
            [0.1, 2.5],
            [0.0, 3.0],
            [0.0, 0.8],
        ])

        def para_params(x):
            return {"k1": float(x[0]), "k2": float(x[1]), "w_batch": float(x[2]), "w_wait": float(x[3])}

        def avaliar_vec(x):
            res = self.simular_linha(jobs, maquinas, proc, setup, "ATCS", para_params(x))
            return self.pontuar_rapido(jobs, res, cap), np.array(x, dtype=float)

        sementes = [
            np.array([1.2, 0.45, 1.6, 0.12]),
            np.array([0.7, 0.25, 2.6, 0.05]),
            np.array([2.4, 1.2, 0.4, 0.35]),
            np.array([1.8, 0.35, 1.0, 0.2]),
        ]
        pop_x = [np.clip(s, limites[:, 0], limites[:, 1]) for s in sementes]
        while len(pop_x) < pop:
            pop_x.append(rng.uniform(limites[:, 0], limites[:, 1]))

        rank = sorted((avaliar_vec(x) for x in pop_x), key=lambda t: t[0])
        melhor = rank[0]
        for _ in range(n_gen):
            elite = [t[1] for t in rank[: max(2, pop // 2)]]
            nova = [melhor[1].copy()]
            while len(nova) < pop:
                p1 = elite[int(rng.integers(0, len(elite)))]
                p2 = elite[int(rng.integers(0, len(elite)))]
                filho = rng.random(4) * p1 + (1.0 - rng.random(4)) * p2
                filho = filho + rng.normal(0, 0.15, size=4) * (limites[:, 1] - limites[:, 0])
                nova.append(np.clip(filho, limites[:, 0], limites[:, 1]))
            rank = sorted((avaliar_vec(x) for x in nova), key=lambda t: t[0])
            if rank[0][0] < melhor[0]:
                melhor = rank[0]
        return para_params(melhor[1])

    def escolher_politica(self, jobs, maquinas, proc, setup, data_base, segmentos, n_gen, pop, seed):
        print("    Ajustando ATCS (setup, prazo, lote e espera)...")
        params = self.otimizar_atcs(jobs, maquinas, proc, setup, segmentos, n_gen=n_gen, pop=pop, seed=seed)
        res_atcs = self.simular_linha(jobs, maquinas, proc, setup, "ATCS", params)
        av_atcs = self.avaliar(jobs, res_atcs, maquinas, data_base, segmentos)
        candidatos = [("ATCS", params, av_atcs, res_atcs)]
        for regra in ("LOTE", "EDD", "SPT"):
            res = self.simular_linha(jobs, maquinas, proc, setup, regra)
            av = self.avaliar(jobs, res, maquinas, data_base, segmentos)
            candidatos.append((regra, {}, av, res))
            print(f"    {regra:<12} lead {av['media_tempo_producao']:.2f} d | "
                  f"delayed {av['total_atrasadas']} | setup {av['setup_total']:.0f} min")
        print(f"    {'ATCS':<12} lead {av_atcs['media_tempo_producao']:.2f} d | "
              f"delayed {av_atcs['total_atrasadas']} | setup {av_atcs['setup_total']:.0f} min | {params}")
        regra, params, av, res = min(candidatos, key=lambda t: self.fitness(t[2]))
        return regra, params, av, res

    def embaralhar_tipos_por_dia(self, df_pendentes, rng):
        df = df_pendentes.copy()
        dias = pd.to_datetime(df["Data entrada"]).dt.normalize()
        for _, idx in df.groupby(dias, sort=False).groups.items():
            pos = list(idx)
            tipos = df.loc[pos, "Tipo de peça"].to_numpy().copy()
            rng.shuffle(tipos)
            df.loc[pos, "Tipo de peça"] = tipos
        return df

    def benchmark(self, df_pendentes, rotas, proc, setup, maquinas, data_base, segmentos,
                  regra, params, n_inst, seed=42):
        if n_inst <= 0:
            vazio = np.array([])
            return vazio, vazio, vazio, {}
        rng = np.random.default_rng(seed)
        prop, linha, maq = [], [], []
        for k in range(n_inst):
            df_k = self.embaralhar_tipos_por_dia(df_pendentes, rng)
            jobs_k = self.montar_jobs(df_k, rotas, proc, data_base, segmentos)
            avs = {}
            for nome, reg, par in (
                ("prop", regra, params),
                ("linha", "FIFO_LINHA", None),
                ("maq", "FIFO_MAQUINA", None),
            ):
                res = self.simular_linha(jobs_k, maquinas, proc, setup, reg, par)
                avs[nome] = self.avaliar(jobs_k, res, maquinas, data_base, segmentos)
            prop.append(avs["prop"]["media_tempo_producao"])
            linha.append(avs["linha"]["media_tempo_producao"])
            maq.append(avs["maq"]["media_tempo_producao"])
            print(f"    mix {k + 1:02d}/{n_inst}: proposta {prop[-1]:.2f} d | "
                  f"FIFO linha {linha[-1]:.2f} d | FIFO máquina {maq[-1]:.2f} d")
        prop, linha, maq = map(np.array, (prop, linha, maq))
        stats = {"vs_linha": self.testar_pares(prop, linha), "vs_maquina": self.testar_pares(prop, maq)}
        return prop, linha, maq, stats

    def projetar_frota(self, jobs, rotas, proc, setup, qtd_inicial, data_base, segmentos, regra, params, passos=6):
        qtd = dict(qtd_inicial)
        historico = []
        av = None
        for passo in range(passos + 1):
            maquinas = self.montar_maquinas(rotas, qtd)
            res = self.simular_linha(jobs, maquinas, proc, setup, regra, params)
            av = self.avaliar(jobs, res, maquinas, data_base, segmentos)
            info = self.gargalo_de(av["df_analise"])
            historico.append({
                "step": passo,
                "machines": sum(qtd.values()),
                "delayed": av["total_atrasadas"],
                "mean_lead_time": round(av["media_tempo_producao"], 2),
                "makespan_working_days": round(av["makespan_dias_uteis"], 2),
                "setup_min": round(av["setup_total"], 1),
                "bottleneck": f"Machine {info['machine_type']}",
                "bottleneck_utilization": round(info["utilization"], 1),
                "units": dict(qtd),
            })
            print(f"    frota passo {passo}: {sum(qtd.values())} máquinas, "
                  f"atrasadas {av['total_atrasadas']}, lead {av['media_tempo_producao']:.2f} d, "
                  f"gargalo Machine {info['machine_type']}")
            if av["total_atrasadas"] == 0 or passo == passos:
                break
            tipo = info["machine_type"] - 1
            qtd[tipo] = qtd.get(tipo, 1) + 1
        return qtd, historico, av

    def cenarios_turno(self, df_pendentes, rotas, proc, setup, frotas, data_base, regra, params):
        linhas = []
        for nome_frota, qtd in frotas:
            maquinas = self.montar_maquinas(rotas, qtd)
            for nome_turno, segmentos in self.config.shifts.items():
                jobs = self.montar_jobs(df_pendentes, rotas, proc, data_base, segmentos)
                for nome_pol, reg, par in (
                    ("Proposed", regra, params),
                    ("FIFO line", "FIFO_LINHA", None),
                ):
                    res = self.simular_linha(jobs, maquinas, proc, setup, reg, par)
                    av = self.avaliar(jobs, res, maquinas, data_base, segmentos)
                    linhas.append({
                        "Fleet": nome_frota,
                        "Calendar": self.config.shift_names[nome_turno],
                        "Useful minutes per day": self.capacidade_dia(segmentos),
                        "Policy": nome_pol,
                        "Mean lead time (days)": round(av["media_tempo_producao"], 2),
                        "Delayed parts": av["total_atrasadas"],
                        "Makespan (working days)": round(av["makespan_dias_uteis"], 2),
                        "Setup (min)": round(av["setup_total"], 1),
                    })
                    print(f"    {nome_frota} | {self.config.shift_names[nome_turno]} | {nome_pol}: "
                          f"lead {av['media_tempo_producao']:.2f} d, atrasadas {av['total_atrasadas']}")
        return pd.DataFrame(linhas)
