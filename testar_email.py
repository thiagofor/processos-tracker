#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testar_email.py

Envia um e-mail de teste usando as mesmas configurações (config.json +
variável de ambiente EMAIL_SENHA) do processos_tracker.py, sem precisar
esperar uma movimentação real em nenhum processo.

Uso:
    python testar_email.py
"""

from datetime import datetime

import processos_tracker as pt


def main() -> None:
    config = pt.carregar_config()
    assunto = "[Processos Tracker] E-mail de teste"
    corpo = (
        f"Este é um e-mail de teste disparado manualmente em "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}.\n\n"
        f"Se você recebeu esta mensagem, a configuração de SMTP e a senha "
        f"de app estão funcionando corretamente."
    )
    pt.enviar_email(config["smtp"], assunto, corpo)


if __name__ == "__main__":
    main()
