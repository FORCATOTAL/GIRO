# Pacote pronto para deploy do app de Relatório de Giro

Este pacote contém arquivos e instruções para publicar o app Streamlit:

- `requirements.txt`: dependências Python
- `Dockerfile` e `.dockerignore`: deploy via Docker/containers
- `Procfile`: deploy em plataformas PaaS (Heroku, Render, Railway)
- `.streamlit/config.toml`: configuração padrão do servidor

## 1) Deploy rápido com Docker (qualquer VPS, inclusive Hostinger)

1. Copie os arquivos do projeto para o servidor (ex.: `/var/www/analises`).
2. Instale Docker no VPS.
3. No diretório do projeto, rode:
   - `docker build -t analises-app .`
   - `docker run -d --name analises-app -p 8501:8501 analises-app`
4. Acesse `http://SEU_IP:8501`.

Observações:
- O container copia todo o projeto, incluindo `GIRO.xlsx`. Se você atualizar o Excel, reconstrua a imagem (`docker build ...`). Alternativamente, monte um volume para persistir/atualizar dados:
  - `docker run -d --name analises-app -p 8501:8501 -v /var/www/analises:/app analises-app`

### Proxy reverso (Nginx) + domínio
- Configure um host no Nginx para apontar para `127.0.0.1:8501` e usar seu domínio (ver guia anterior).
- SSL (Let’s Encrypt): `sudo certbot --nginx -d relatorio.seudominio.com`.

## 2) Deploy manual sem Docker (VPS Ubuntu/Hostinger)

1. Instale dependências: `sudo apt update && sudo apt install -y python3-pip python3-venv nginx`
2. Crie pasta do app: `sudo mkdir -p /var/www/analises && sudo chown $USER:$USER /var/www/analises`
3. Copie os arquivos do projeto para `/var/www/analises`.
4. Ambiente virtual e libs:
   - `cd /var/www/analises`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
5. Teste: `.venv/bin/streamlit run tela_relatorio.py --server.headless true --server.address 0.0.0.0 --server.port 8501`
6. Configure como serviço (systemd) para iniciar automaticamente:
   - Crie `/etc/systemd/system/streamlit.service` com:
```
[Unit]
Description=Streamlit Analises
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/analises
Environment="PATH=/var/www/analises/.venv/bin"
ExecStart=/var/www/analises/.venv/bin/streamlit run tela_relatorio.py --server.headless true --server.address 0.0.0.0 --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```
   - `sudo systemctl daemon-reload && sudo systemctl enable streamlit && sudo systemctl start streamlit`
   - Logs: `sudo journalctl -u streamlit -f`
7. Nginx proxy e DNS: igual ao passo do Docker.

## 3) PaaS (Heroku/Render/Railway)

- Use o `Procfile` e `requirements.txt`.
- Heroku (exemplo):
  - `heroku create` e `heroku git:remote -a <appname>`
  - `git add . && git commit -m "deploy" && git push heroku main`
- Render/Railway: aponte o comando de start para:
  - `streamlit run tela_relatorio.py --server.headless true --server.address 0.0.0.0 --server.port $PORT`

## Dados do relatório

- Coloque `GIRO.xlsx` no diretório do app.
- O relatório gerado (`RELATORIO_GIRO_MENSAL.xlsx`) pode ser criado pela UI (botão) ou executando `python relatorio_giro_mensal.py`.

## Dicas de operação

- Atualizar dependências: `pip install -r requirements.txt`
- Reiniciar serviço: `sudo systemctl restart streamlit`
- Logs do app: via `journalctl` (systemd) ou `docker logs -f analises-app`.

## Segurança

- Opcional: proteger acesso com autenticação básica via Nginx (htpasswd).
- Monitore uso de memória/CPU. Streamlit é leve, mas tabelas grandes podem impactar.

---

Se precisar, posso automatizar ainda mais com um `docker-compose.yml` e scripts de provisionamento (Nginx + certbot) para Hostinger.