#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processos_tracker.py

Acompanha processos no TJMG (ou qualquer outro tribunal) usando a API Pública
do DataJud (CNJ) e envia um e-mail de alerta quando surge movimentação nova.

Fonte de dados: API Pública do DataJud (oficial, mantida pelo CNJ)
https://datajud-wiki.cnj.jus.br/api-publica/acesso/

Uso:
    python processos_tracker.py            # roda uma verificação e sai
    python processos_tracker.py --once      # idem (explícito)
    python processos_tracker.py --loop 6h   # roda em loop a cada 6 horas

Configuração:
    - Edite config.json (veja config.exemplo.json) com os números dos processos.
    - Defina as variáveis de ambiente antes de rodar (veja README.md):
        DATAJUD_API_KEY   (opcional - tem um valor público padrão)
        EMAIL_SENHA       (senha de app do e-mail remetente)
"""

from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import requests

# Suporte opcional a arquivo .env (não é obrigatório ter a lib instalada)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ImportError:
    pass

# --------------------------------------------------------------------------- #
# Configuração e constantes
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ESTADO_PATH = BASE_DIR / "estado_processos.json"
LOG_PATH = BASE_DIR / "processos_tracker.log"

DATAJUD_URL_BASE = "https://api-publica.datajud.cnj.jus.br"

# Chave pública oficial divulgada pelo CNJ (pode mudar; confira em
# https://datajud-wiki.cnj.jus.br/api-publica/acesso/ e sobrescreva via
# variável de ambiente DATAJUD_API_KEY se necessário).
DATAJUD_API_KEY_PADRAO = (
    "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("processos_tracker")


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #

@dataclass
class Movimento:
    codigo: int | None
    nome: str
    data_hora: str  # string ISO como vem da API, ex: 2026-08-01T10:23:00.000Z

    @property
    def timestamp(self) -> datetime:
        # Normaliza formatos "...Z" e com/sem microssegundos
        texto = self.data_hora.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(texto)
        except ValueError:
            # fallback simples caso o formato varie
            return datetime.min

    def __str__(self) -> str:
        try:
            dt = self.timestamp.strftime("%d/%m/%Y %H:%M")
        except Exception:
            dt = self.data_hora
        return f"[{dt}] {self.nome}"


@dataclass
class ResultadoProcesso:
    numero: str
    encontrado: bool = False
    erro: str | None = None
    movimentos: list[Movimento] = field(default_factory=list)
    classe: str | None = None
    orgao_julgador: str | None = None


# --------------------------------------------------------------------------- #
# Consulta à API DataJud
# --------------------------------------------------------------------------- #

def limpar_numero_processo(numero: str) -> str:
    """Remove pontuação, deixando só os 20 dígitos exigidos pela API."""
    return re.sub(r"\D", "", numero)


def consultar_processo(
    numero_processo: str, tribunal: str, api_key: str, timeout: int = 15
) -> ResultadoProcesso:
    """Consulta um processo na API Pública do DataJud."""
    numero_limpo = limpar_numero_processo(numero_processo)
    url = f"{DATAJUD_URL_BASE}/api_publica_{tribunal.lower()}/_search"
    headers = {
        "Authorization": f"APIKey {api_key}",
        "Content-Type": "application/json",
    }
    corpo = {"query": {"match": {"numeroProcesso": numero_limpo}}}

    resultado = ResultadoProcesso(numero=numero_processo)

    try:
        resp = requests.post(url, headers=headers, json=corpo, timeout=timeout)
    except requests.RequestException as exc:
        resultado.erro = f"Falha de conexão: {exc}"
        return resultado

    if resp.status_code != 200:
        resultado.erro = f"HTTP {resp.status_code}: {resp.text[:300]}"
        return resultado

    dados = resp.json()
    hits = dados.get("hits", {}).get("hits", [])
    if not hits:
        resultado.erro = "Processo não encontrado (ou sigiloso / número incorreto)"
        return resultado

    fonte = hits[0].get("_source", {})
    resultado.encontrado = True
    resultado.classe = (fonte.get("classe") or {}).get("nome")
    resultado.orgao_julgador = (fonte.get("orgaoJulgador") or {}).get("nome")

    movimentos_brutos = fonte.get("movimentos", []) or []
    movimentos = [
        Movimento(
            codigo=m.get("codigo"),
            nome=m.get("nome", "Movimentação sem descrição"),
            data_hora=m.get("dataHora", ""),
        )
        for m in movimentos_brutos
    ]
    movimentos.sort(key=lambda m: m.timestamp)
    resultado.movimentos = movimentos
    return resultado


# --------------------------------------------------------------------------- #
# Persistência do estado (o que já vimos antes)
# --------------------------------------------------------------------------- #

def carregar_estado() -> dict[str, Any]:
    if ESTADO_PATH.exists():
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_estado(estado: dict[str, Any]) -> None:
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# E-mail de alerta
# --------------------------------------------------------------------------- #

def enviar_email(config_smtp: dict[str, Any], assunto: str, corpo: str) -> None:
    senha = os.environ.get("EMAIL_SENHA")
    if not senha:
        log.warning(
            "EMAIL_SENHA não definida no ambiente — pulando envio de e-mail. "
            "Veja o README.md para configurar."
        )
        return

    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = config_smtp["usuario"]
    msg["To"] = config_smtp["destinatario"]

    try:
        with smtplib.SMTP(config_smtp["servidor"], config_smtp["porta"]) as servidor:
            servidor.starttls()
            servidor.login(config_smtp["usuario"], senha)
            servidor.send_message(msg)
        log.info("E-mail de alerta enviado para %s", config_smtp["destinatario"])
    except Exception as exc:
        log.error("Falha ao enviar e-mail: %s", exc)


# --------------------------------------------------------------------------- #
# Lógica principal
# --------------------------------------------------------------------------- #

def carregar_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        log.error(
            "config.json não encontrado. Copie config.exemplo.json para "
            "config.json e preencha com seus dados."
        )
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def rodar_verificacao() -> None:
    config = carregar_config()
    processos: list[str] = config["processos"]
    tribunal: str = config.get("tribunal", "tjmg")
    api_key = os.environ.get("DATAJUD_API_KEY", DATAJUD_API_KEY_PADRAO)
    delay_entre_consultas = config.get("delay_segundos_entre_consultas", 1.5)

    estado = carregar_estado()
    novidades: list[str] = []

    for numero in processos:
        log.info("Consultando processo %s (%s)...", numero, tribunal)
        resultado = consultar_processo(numero, tribunal, api_key)

        if resultado.erro:
            log.warning("  -> %s", resultado.erro)
            time.sleep(delay_entre_consultas)
            continue

        if not resultado.movimentos:
            log.info("  -> Nenhuma movimentação retornada pela API.")
            time.sleep(delay_entre_consultas)
            continue

        ultima_conhecida = estado.get(numero, {}).get("ultima_movimentacao")
        novos_movimentos = [
            m
            for m in resultado.movimentos
            if ultima_conhecida is None or m.data_hora > ultima_conhecida
        ]

        if ultima_conhecida is None:
            # Primeira vez que vemos este processo: só grava a linha de base,
            # sem gerar alerta (senão o histórico inteiro viraria "novidade").
            log.info(
                "  -> Primeira consulta deste processo: %d movimentações "
                "carregadas como linha de base.",
                len(resultado.movimentos),
            )
        elif novos_movimentos:
            log.info("  -> %d movimentação(ões) nova(s)!", len(novos_movimentos))
            bloco = [f"Processo: {numero}"]
            if resultado.classe:
                bloco.append(f"Classe: {resultado.classe}")
            if resultado.orgao_julgador:
                bloco.append(f"Órgão julgador: {resultado.orgao_julgador}")
            bloco.append("Movimentações novas:")
            bloco.extend(f"  - {m}" for m in novos_movimentos)
            novidades.append("\n".join(bloco))
        else:
            log.info("  -> Sem novidades.")

        estado[numero] = {
            "ultima_movimentacao": resultado.movimentos[-1].data_hora,
            "verificado_em": datetime.now().isoformat(timespec="seconds"),
        }
        time.sleep(delay_entre_consultas)

    salvar_estado(estado)

    if novidades:
        corpo = (
            f"Foram encontradas movimentações novas em {len(novidades)} "
            f"processo(s):\n\n" + "\n\n---\n\n".join(novidades)
        )
        assunto = f"[Processos] {len(novidades)} atualização(ões) encontrada(s)"
        enviar_email(config["smtp"], assunto, corpo)
    else:
        log.info("Verificação concluída. Nenhuma novidade para reportar.")


def parse_intervalo(texto: str) -> float:
    """Converte algo como '6h', '30m', '90s' para segundos."""
    unidade = texto[-1].lower()
    valor = float(texto[:-1])
    fatores = {"s": 1, "m": 60, "h": 3600}
    if unidade not in fatores:
        raise ValueError(f"Intervalo inválido: {texto!r} (use sufixo s, m ou h)")
    return valor * fatores[unidade]


def main() -> None:
    argumentos = sys.argv[1:]

    if "--loop" in argumentos:
        idx = argumentos.index("--loop")
        try:
            intervalo_texto = argumentos[idx + 1]
        except IndexError:
            print("Uso: --loop <intervalo>, ex: --loop 6h")
            sys.exit(1)
        intervalo_segundos = parse_intervalo(intervalo_texto)
        log.info("Iniciando loop contínuo a cada %s.", intervalo_texto)
        while True:
            rodar_verificacao()
            log.info("Aguardando %s até a próxima verificação...", intervalo_texto)
            time.sleep(intervalo_segundos)
    else:
        rodar_verificacao()


if __name__ == "__main__":
    main()
