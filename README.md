# Processos Tracker (TJMG / DataJud)

Script simples para acompanhar processos judiciais e avisar por e-mail quando
sair movimentação nova. Usa a **API Pública do DataJud (CNJ)** — fonte oficial,
sem necessidade de login, senha de advogado ou resolução de CAPTCHA.

> A API Pública do DataJud cobre TJMG e praticamente todos os tribunais do
> país (troque o campo `"tribunal"` no config para usar em outro TJ/TRT/TRF —
> ex.: `"tjsp"`, `"trf1"`, `"trt3"`).

## 1. Instalar dependências

```bash
pip install -r requirements.txt
```
## 2. Executar via Interface Web (Recomendado)

Para abrir o painel de controlo interativo no navegador:

```bash
streamlit run app.py
```

No Windows, também pode simplesmente dar duplo clique no ficheiro iniciar_app.bat.

### Recursos da Interface Web:
- Estado Atual: Exibe os processos com formatação compacta e legível contendo metadados completos (Classe, Órgão Julgador, Sistema, Data de Ajuizamento formatada, Assuntos e Última Movimentação).
- Gerir Processos: Adicionar ou remover números de processos sem necessidade de editar ficheiros JSON manualmente.
- Definições: Ajustar tribunal, atraso de rede, credenciais SMTP e guardar a Senha de App do Gmail de forma segura diretamente no ficheiro .env.
- Logs: Visualizador em tempo real dos registos de execução (processos_tracker.log).


## 3. Configuração Manual (Sem Interface)

### 3.1. Processos (config.json)
Copie o ficheiro de exemplo e edite com os números reais:

```bash
cp config.exemplo.json config.json
```

```json
{
  "tribunal": "tjmg",
  "processos": [
    "5001234-56.2024.8.13.0024"
  ],
  "delay_segundos_entre_consultas": 1.5,
  "smtp": {
    "servidor": "smtp.gmail.com",
    "porta": 587,
    "usuario": "seu_email@gmail.com",
    "destinatario": "seu_email@gmail.com"
  }
}
```

### 3.2. Senha de E-mail (.env)
Crie um arquivo com o nome exato .env na raiz do projeto com a sua Senha de Aplicação do Gmail:

```bash
EMAIL_SENHA=sua_senha_de_app
```

(Nota: Se utilizar a Interface Web, esta variável é gravada automaticamente no .env ao salvar as definições).

> ⚠️ No Windows é fácil o Explorer salvar como `.env.txt` ou o arquivo acabar
> com outro nome (ex.: `EMAIL_SENHA.env`) — nesse caso o `python-dotenv` não
> encontra o arquivo e a variável não é carregada. Confirme com
> `Get-ChildItem -Force` no PowerShell que o nome está exatamente `.env`.

A chave da API do DataJud já vem com um valor público padrão embutido no
script. Se o CNJ trocar essa chave e o script parar de funcionar, pegue a nova
em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ e defina
`DATAJUD_API_KEY` do mesmo jeito que `EMAIL_SENHA`.

## 4. Executar via Linha de Comando

Execução Única:

```bash
python processos_tracker.py
```

Na primeira execução, o script só grava a "linha de base" das movimentações
de cada processo (não dispara e-mail — senão o histórico inteiro seria
tratado como novidade). Da segunda execução em diante, qualquer movimentação
posterior à última vista gera alerta.

Para rodar em loop contínuo em vez de uma vez só:
```bash
python processos_tracker.py --loop 6h
```

## 4.1 Testar só o envio de e-mail

Pra confirmar que a senha de app e o SMTP estão certos sem precisar esperar
uma movimentação real:

```bash
python testar_email.py
```

Ele usa o mesmo `config.json` e a mesma `EMAIL_SENHA`/`.env` do script
principal e manda um e-mail de teste avulso.

## 5. Automação e Segundo Plano

### Windows (Agendador de Tarefas — Recomendado)
Crie uma tarefa para executar python.exe processos_tracker.py apontando o campo "Iniciar em" para a pasta do projeto. Defina a frequência desejada (ex.: a cada 6 horas).

### Windows (Modo Oculto / Sem Janela Aberta)
Para rodar o loop contínuo em segundo plano sem manter a janela de terminal aberta, pode criar e executar um ficheiro iniciar_oculto.vbs:

```bash
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe processos_tracker.py --loop 6h", 0, False
```

### Linux / Mac (cron)
Exemplo para rodar diariamente às 08:00:

```bash
0 8 * * * cd /caminho/para/processos_tracker && /usr/bin/python3 processos_tracker.py >> cron.log 2>&1
```


## Arquivos do Projeto

- app.py: Interface gráfica Web desenvolvida em Streamlit.
- processos_tracker.py: Script principal com lógica de consulta, retentativas automáticas contra instabilidades da API e envio de alertas.
- iniciar_app.bat: Script de atalho para iniciar o servidor web no Windows.
- estado_processos.json: Armazena a linha de base e os metadados dos processos consultados.
- processos_tracker.log: Ficheiro de logs de execução do sistema.


## Limitações e Notas
- A API pública do DataJud pode apresentar momentos de lentidão ou indisponibilidade temporária. O script conta com mecanismos de retentativa e tempo de espera (timeout) estendido de 30 segundos.
- Processos em segredo de justiça não são disponibilizados pela API pública do CNJ.
- Esta ferramenta funciona como um radar de acompanhamento e não substitui as publicações nos diários oficiais nem as intimações formais do tribunal.
