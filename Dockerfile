# Base leve com Python
FROM python:3.11-slim

# Evitar prompts e reduzir cache
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

# Dependências do sistema (opcional, útil para fontes/locale)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    locales \
 && rm -rf /var/lib/apt/lists/* \
 && sed -i 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen

ENV LANG=pt_BR.UTF-8 \
    LANGUAGE=pt_BR:pt:en \
    LC_ALL=pt_BR.UTF-8

WORKDIR /app

# Copiar dependências primeiro para melhor cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar app
COPY . /app

# Expor porta do Streamlit
EXPOSE 8501

# Comando de execução
CMD ["streamlit", "run", "tela_relatorio.py", "--server.headless", "true", "--server.address", "0.0.0.0", "--server.port", "8501"]