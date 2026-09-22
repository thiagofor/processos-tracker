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

## 2. Configurar os processos

Copie o arquivo de exemplo e edite com os números reais (formato CNJ, com ou
sem pontuação — o script limpa sozinho):

```bash
cp config.exemplo.json config.json
```

```json
{
  "tribunal": "tjmg",
  "processos": [
    "5001234-56.2024.8.13.0024"
  ],
  "smtp": {
    "servidor": "smtp.gmail.com",
    "porta": 587,
    "usuario": "seu_email@gmail.com",
    "destinatario": "seu_email@gmail.com"
  }
}
```

## 3. Configurar a senha de e-mail (nunca no config.json!)

Defina a variável de ambiente `EMAIL_SENHA` antes de rodar. Se o remetente for
Gmail, **não use a senha normal** — gere uma "senha de app" em
myaccount.google.com/apppasswords (precisa de verificação em duas etapas
ativada).

Linux/Mac:
```bash
export EMAIL_SENHA="sua_senha_de_app"
```

Windows (PowerShell):
```powershell
$env:EMAIL_SENHA = "sua_senha_de_app"
```

Alternativa: crie um arquivo `.env` na mesma pasta (o script já lê sozinho, se
`python-dotenv` estiver instalado):
```
EMAIL_SENHA=sua_senha_de_app
```

A chave da API do DataJud já vem com um valor público padrão embutido no
script. Se o CNJ trocar essa chave e o script parar de funcionar, pegue a nova
em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ e defina
`DATAJUD_API_KEY` do mesmo jeito que `EMAIL_SENHA`.

## 4. Rodar

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

## 5. Automatizar (recomendado em vez do --loop)

**Linux/Mac (cron)** — roda todo dia às 8h:
```
0 8 * * * cd /caminho/para/processos_tracker && /usr/bin/python3 processos_tracker.py >> cron.log 2>&1
```

**Windows (Agendador de Tarefas)**: crie uma tarefa que execute
`python.exe processos_tracker.py` com "Iniciar em" apontando para a pasta do
script, no gatilho e frequência que preferir. Lembre-se de configurar
`EMAIL_SENHA` como variável de ambiente do sistema (ou usar um `.env`), já que
tarefas agendadas não herdam variáveis definidas manualmente no terminal.

## Arquivos gerados automaticamente

- `estado_processos.json`: guarda a última movimentação vista de cada
  processo. Não apague, ou o script vai reenviar o histórico todo como
  "novidade" na próxima rodada.
- `processos_tracker.log`: log de cada execução.

## Limitações

- A API DataJud é alimentada pelos tribunais e pode ter atraso de replicação
  em relação ao sistema interno (PJe/e-SAJ) — normalmente de poucas horas.
- Processos em segredo de justiça não aparecem na consulta pública.
- Fica a seu critério confirmar prazos processuais oficiais direto no sistema
  do tribunal antes de qualquer decisão importante; o script é só um radar de
  monitoramento, não substitui a intimação oficial.
