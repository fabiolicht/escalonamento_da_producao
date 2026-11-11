import os
import pandas as pd


class DataMixin:
    def carregar_planilha(self):
        caminho = os.path.join(self.config.base_dir, "pecas.xlsx")
        df_entrada = pd.read_excel(caminho, sheet_name="Entrada")
        df_dados = pd.read_excel(caminho, sheet_name="Dados")
        df_dados.columns = df_dados.columns.str.strip()
        df_entrada["Data entrada"] = pd.to_datetime(df_entrada["Data entrada"])
        return df_entrada, df_dados

    def extrair_rotas_e_tempos(self, df_dados):
        rotas = {}
        for _, row in df_dados.dropna(subset=["Peças", "Rota da Peça"]).iterrows():
            tipo = str(row["Peças"]).strip()
            rota_txt = str(row["Rota da Peça"]).strip()
            if tipo.lower() == "nan" or rota_txt.lower() == "nan":
                continue
            rotas[tipo] = [int(x.strip()) for x in rota_txt.split(",")]

        proc, setup = {}, {}
        for _, row in df_dados.dropna(subset=["Máquinas"]).iterrows():
            try:
                maq = int(row["Máquinas"])
                proc[maq] = int(round(float(row["Tempo de máquina (min)"])))
                setup[maq] = int(round(float(row["Tempo de troca de peças"])))
            except (TypeError, ValueError):
                continue

        faltando = sorted({m for rota in rotas.values() for m in rota if m not in proc})
        if faltando:
            raise ValueError(f"Rota cita máquina sem tempo: {faltando}")
        return rotas, proc, setup

    def aumentar_frota_no_gargalo(self, qtd, machine_type):
        nova_qtd = dict(qtd)
        tipo = machine_type - 1
        if tipo not in nova_qtd:
            raise ValueError(f"Gargalo Machine {machine_type} não consta na frota.")
        nova_qtd[tipo] += 1
        return nova_qtd

    def montar_maquinas(self, rotas, qtd):
        maquinas = []
        for tipo in sorted({m for rota in rotas.values() for m in rota}):
            n = int(qtd.get(tipo, 1))
            for u in range(n):
                nome = f"Machine {tipo + 1} (Unit {u + 1})" if n > 1 else f"Machine {tipo + 1}"
                maquinas.append({"tipo": tipo, "id": len(maquinas), "nome": nome, "unidade": u + 1})
        return maquinas

    def montar_jobs(self, df_pendentes, rotas, proc, data_base, segmentos):
        df = df_pendentes.sort_values(["Data entrada"], kind="mergesort")
        jobs = []
        for ordem, (orig_idx, row) in enumerate(df.iterrows()):
            tipo = str(row["Tipo de peça"]).strip()
            if tipo not in rotas:
                raise ValueError(f"Tipo de peça sem rota: {tipo}")
            chegada = pd.Timestamp(row["Data entrada"])
            release = self.data_para_minutos_uteis(chegada, data_base, segmentos)
            prazo = chegada.normalize() + pd.Timedelta(days=self.config.deadline_days)
            due = self.data_para_minutos_uteis(prazo, data_base, segmentos)
            rota = list(rotas[tipo])
            jobs.append({
                "orig_idx": orig_idx,
                "ordem": ordem,
                "tipo": tipo,
                "release": int(release),
                "due": int(due),
                "chegada": chegada,
                "prazo": prazo.to_pydatetime(),
                "rota": rota,
                "trabalho": int(sum(proc[m] for m in rota)),
            })
        return jobs
