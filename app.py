import json
import os
import streamlit as st
from datetime import datetime
import processos_tracker as pt

st.set_page_config(
    page_title="Processos Tracker",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Processos Tracker - Painel de Controle")


def guardar_senha_env(senha: str):
    """Guarda ou atualiza a variável EMAIL_SENHA no ficheiro .env na raiz do projeto."""
    env_path = pt.BASE_DIR / ".env"
    linhas = []
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
            
    linhas_filtradas = [l for l in linhas if not l.startswith("EMAIL_SENHA=")]
    linhas_filtradas.append(f"EMAIL_SENHA={senha}\n")
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(linhas_filtradas)
        
    os.environ["EMAIL_SENHA"] = senha


def formatar_data(val: str | None) -> str:
    """Converte formatos de data (brutos ou ISO) para DD/MM/AAAA às HH:mm."""
    if not val:
        return "Não informada"
    
    val_clean = str(val).strip()
    
    # Trata formato numérico compacto (ex: 20230511160558 -> 11/05/2023 às 16:05)
    if len(val_clean) >= 8 and val_clean[:8].isdigit():
        try:
            ano, mes, dia = val_clean[:4], val_clean[4:6], val_clean[6:8]
            hora = val_clean[8:10] if len(val_clean) >= 10 else ""
            minuto = val_clean[10:12] if len(val_clean) >= 12 else ""
            
            data_str = f"{dia}/{mes}/{ano}"
            if hora and minuto:
                data_str += f" às {hora}:{minuto}"
            return data_str
        except Exception:
            pass

    # Trata formato ISO (ex: 2023-10-31T14:03:55.000Z ou 2026-09-22T14:14:48)
    try:
        texto = val_clean.replace("Z", "+00:00")
        dt = datetime.fromisoformat(texto)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return val_clean


# Carregar ou inicializar configurações
if pt.CONFIG_PATH.exists():
    config = pt.carregar_config()
else:
    config = {
        "tribunal": "tjmg",
        "processos": [],
        "delay_segundos_entre_consultas": 1.5,
        "smtp": {
            "servidor": "smtp.gmail.com",
            "porta": 587,
            "usuario": "",
            "destinatario": ""
        }
    }

# Separadores principais
tab_dashboard, tab_processos, tab_config, tab_logs = st.tabs([
    "📊 Estado Atual", 
    "📜 Gerir Processos", 
    "⚙️ Definições", 
    "📋 Logs do Sistema"
])

# --------------------------------------------------------------------------- #
# Tab 1: Estado Atual e Execução
# --------------------------------------------------------------------------- #
with tab_dashboard:
    st.subheader("Acompanhamento de Processos")
    
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("🚀 Verificação Manual", type="primary", use_container_width=True):
            with st.spinner("A consultar API do DataJud..."):
                pt.rodar_verificacao()
            st.success("Verificação concluída!")
            st.rerun()

    estado = pt.carregar_estado()
    if estado:
        for numero, info in estado.items():
            with st.expander(f"📌 Processo: {numero}", expanded=True):
                data_aj = formatar_data(info.get('data_ajuizamento'))
                data_mov = formatar_data(info.get('ultima_movimentacao'))
                data_ver = formatar_data(info.get('verificado_em'))
                assuntos = info.get('assuntos', [])
                assuntos_str = ', '.join(assuntos) if assuntos else 'Não informado'

                html_conteudo = f"""
                <style>
                    .proc-container {{
                        line-height: 1.35;
                        font-size: 0.95rem;
                        margin-bottom: 5px;
                    }}
                    .proc-container b {{
                        color: #FAFAFA;
                    }}
                </style>
                <div class="proc-container">
                    <div style="display: flex; gap: 20px;">
                        <div style="flex: 1;">
                            <p style="margin: 3px 0;"><b>Classe:</b> {info.get('classe') or 'Não informada'}</p>
                            <p style="margin: 3px 0;"><b>Órgão Julgador:</b> {info.get('orgao_julgador') or 'Não informado'}</p>
                            <p style="margin: 3px 0;"><b>Sistema:</b> {info.get('sistema') or 'Não informado'}</p>
                        </div>
                        <div style="flex: 1;">
                            <p style="margin: 3px 0;"><b>Data de Ajuizamento:</b> {data_aj}</p>
                            <p style="margin: 3px 0;"><b>Assunto(s):</b> {assuntos_str}</p>
                        </div>
                    </div>
                    <hr style="margin: 10px 0; border-color: #333;">
                    <p style="margin: 3px 0;"><b>Última movimentação registada:</b> <code>{data_mov}</code></p>
                    <p style="margin: 3px 0;"><b>Última verificação:</b> {data_ver}</p>
                </div>
                """
                st.markdown(html_conteudo, unsafe_allow_html=True)
    else:
        st.info("Nenhum estado guardado. Clique em 'Verificação Manual' para carregar a linha de base.")

# --------------------------------------------------------------------------- #
# Tab 2: Gestão de Processos
# --------------------------------------------------------------------------- #
with tab_processos:
    st.subheader("Adicionar ou Remover Processos")

    with st.form("form_novo_processo", clear_on_submit=True):
        novo_num = st.text_input("Número do Processo (Formato CNJ ou apenas números)")
        submetido = st.form_submit_button("Adicionar Processo")

        if submetido and novo_num:
            num_limpo = pt.limpar_numero_processo(novo_num)
            if num_limpo not in [pt.limpar_numero_processo(p) for p in config.get("processos", [])]:
                config.setdefault("processos", []).append(novo_num)
                with open(pt.CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                st.success(f"Processo {novo_num} adicionado com sucesso!")
                st.rerun()
            else:
                st.warning("Este processo já está na lista de monitorização.")

    st.markdown("---")
    st.write("### Processos em Monitorização")

    for idx, proc in enumerate(config.get("processos", [])):
        col_txt, col_del = st.columns([5, 1])
        col_txt.code(proc)
        if col_del.button("❌ Remover", key=f"del_{idx}"):
            config["processos"].remove(proc)
            with open(pt.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            st.rerun()

# --------------------------------------------------------------------------- #
# Tab 3: Configurações Gerais e SMTP
# --------------------------------------------------------------------------- #
with tab_config:
    st.subheader("Definições da Aplicação")

    tribunal = st.text_input("Tribunal (ex: tjmg, tjsp, trf1)", value=config.get("tribunal", "tjmg"))
    delay = st.number_input(
        "Intervalo entre consultas (segundos)", 
        value=float(config.get("delay_segundos_entre_consultas", 1.5)),
        min_value=0.5,
        step=0.5
    )

    st.markdown("---")
    st.subheader("Configuração de Alerta por E-mail (SMTP)")

    smtp_conf = config.get("smtp", {})
    usuario = st.text_input("E-mail Remetente", value=smtp_conf.get("usuario", ""))
    destinatario = st.text_input("E-mail Destinatário", value=smtp_conf.get("destinatario", ""))
    servidor = st.text_input("Servidor SMTP", value=smtp_conf.get("servidor", "smtp.gmail.com"))
    porta = st.number_input("Porta SMTP", value=int(smtp_conf.get("porta", 587)))

    senha_atual = os.environ.get("EMAIL_SENHA", "")
    senha_app = st.text_input(
        "Senha de App do Gmail (Guardada no .env)", 
        value=senha_atual, 
        type="password",
        help="Gere uma senha de aplicação em myaccount.google.com/apppasswords"
    )

    if st.button("Guardar Definições", type="primary"):
        config["tribunal"] = tribunal
        config["delay_segundos_entre_consultas"] = delay
        config["smtp"] = {
            "servidor": servidor,
            "porta": porta,
            "usuario": usuario,
            "destinatario": destinatario
        }
        with open(pt.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        if senha_app:
            guardar_senha_env(senha_app)

        st.success("Definições e ficheiro .env atualizados com sucesso!")

# --------------------------------------------------------------------------- #
# Tab 4: Leitor de Logs
# --------------------------------------------------------------------------- #
with tab_logs:
    st.subheader("Histórico de Execução (processos_tracker.log)")
    if pt.LOG_PATH.exists():
        with open(pt.LOG_PATH, "r", encoding="utf-8") as f:
            linhas = f.readlines()
            st.text_area("Logs", value="".join(reversed(linhas)), height=400)
    else:
        st.info("Nenhum ficheiro de log gerado até ao momento.")