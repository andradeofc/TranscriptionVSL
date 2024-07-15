# Usar uma imagem base do Python
FROM python:3.9

# Instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Definir o diretório de trabalho no contêiner
WORKDIR /app

# Copiar o requirements.txt e instalar as dependências
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar o restante do código da aplicação para o diretório de trabalho
COPY . .

# Expor a porta que a aplicação usará
EXPOSE 8080

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
