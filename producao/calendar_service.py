from datetime import datetime
import numpy as np
import pandas as pd


class CalendarMixin:
    def capacidade_dia(self, segmentos):
        return int(sum(b - a for a, b in segmentos))

    def alinhar_dia_util(self, data):
        dia = pd.Timestamp(data).normalize()
        while int(dia.weekday()) >= 5:
            dia += pd.Timedelta(days=1)
        return dia

    def avancar_dias_uteis(self, dia, n_dias):
        atual = pd.Timestamp(dia).normalize()
        faltam = int(n_dias)
        while faltam > 0:
            atual += pd.Timedelta(days=1)
            if int(atual.weekday()) < 5:
                faltam -= 1
        while int(atual.weekday()) >= 5:
            atual += pd.Timedelta(days=1)
        return atual

    def minutos_do_dia_para_data(self, dia, minuto_abs):
        extra, minuto = divmod(int(minuto_abs), 24 * 60)
        base = pd.Timestamp(dia).normalize() + pd.Timedelta(days=extra)
        return (base + pd.Timedelta(minutes=minuto)).to_pydatetime()

    def minutos_uteis_para_data(self, minutos, data_base, segmentos, fim_de_operacao=False):
        """Converte minutos úteis em data e hora.

        O índice t como início é o começo daquele minuto útil (240 → 13:00).
        O mesmo índice como fim de operação é o instante em que o trabalho termina
        (240 → 12:00). Sem essa distinção o almoço cola o fim da manhã no início da tarde.
        """
        cap = self.capacidade_dia(segmentos)
        minutos = int(minutos)
        dia = self.alinhar_dia_util(data_base)
        if minutos <= 0:
            return self.minutos_do_dia_para_data(dia, segmentos[0][0])

        dias, resto = divmod(minutos, cap)
        if fim_de_operacao and resto == 0:
            dias -= 1
            resto = cap
        dia = self.avancar_dias_uteis(dia, dias) if dias > 0 else dia

        if not fim_de_operacao:
            for inicio, fim in segmentos:
                dur = fim - inicio
                if resto < dur:
                    return self.minutos_do_dia_para_data(dia, inicio + resto)
                resto -= dur
            return self.minutos_do_dia_para_data(dia, segmentos[0][0])

        for inicio, fim in segmentos:
            dur = fim - inicio
            if resto <= dur:
                return self.minutos_do_dia_para_data(dia, inicio + resto)
            resto -= dur
        return self.minutos_do_dia_para_data(dia, segmentos[-1][1])

    def data_para_minutos_uteis(self, data_alvo, data_base, segmentos):
        """Minutos úteis entre o início do expediente de data_base e o de data_alvo."""
        cap = self.capacidade_dia(segmentos)
        alvo = pd.Timestamp(data_alvo).normalize()
        base = self.alinhar_dia_util(data_base)
        if alvo <= base:
            return 0
        n = int(np.busday_count(base.date(), alvo.date()))
        return n * cap

    def verificar_calendario(self):
        base = datetime(2026, 11, 9)
        seg = self.config.shifts["1_turno"]
        assert self.minutos_uteis_para_data(0, base, seg, False) == datetime(2026, 11, 9, 8, 0)
        assert self.minutos_uteis_para_data(240, base, seg, True) == datetime(2026, 11, 9, 12, 0)
        assert self.minutos_uteis_para_data(240, base, seg, False) == datetime(2026, 11, 9, 13, 0)
        assert self.minutos_uteis_para_data(480, base, seg, True) == datetime(2026, 11, 9, 17, 0)
        assert self.minutos_uteis_para_data(480, base, seg, False) == datetime(2026, 11, 10, 8, 0)
        assert self.minutos_uteis_para_data(2400, base, seg, True) == datetime(2026, 11, 13, 17, 0)
        assert self.minutos_uteis_para_data(2400, base, seg, False) == datetime(2026, 11, 16, 8, 0)
        assert self.capacidade_dia(self.config.shifts["hora_extra"]) == 600
        assert self.capacidade_dia(self.config.shifts["dois_turnos"]) == 960
