FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema necessárias para PlatformIO
# git: para baixar bibliotecas
# build-essential: ferramentas de compilação
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar PlatformIO CLI
RUN pip install --no-cache-dir platformio

# Copiar código da aplicação
COPY main.py .
COPY sensor_catalog.py .
COPY firmware_builder.py .
COPY static/ static/

# Volume para persistência do SQLite e builds
VOLUME ["/data"]

# Expor porta
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["python", "-u", "main.py"]
