FROM python:3.12-slim

WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY main.py .
COPY static/ static/

# Volume para persistência do SQLite
VOLUME ["/data"]

# Expor porta
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["python", "-u", "main.py"]
