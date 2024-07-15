# Flask Audio Processing App

## Requisitos

- Docker instalado

## Instruções para Executar

1. Clone este repositório:
    ```sh
    git clone <URL_DO_REPOSITORIO>
    cd <NOME_DO_DIRETORIO>
    ```

2. Construa a imagem Docker:
    ```sh
    docker build -t flask-audio-app .
    ```

3. Execute o contêiner Docker:
    ```sh
    docker run -p 5000:5000 flask-audio-app
    ```

4. Acesse a aplicação em seu navegador:
    ```
    http://localhost:5000
    ```

## Implantação com Replit

1. Crie um novo projeto no Replit.
2. Faça upload dos arquivos do projeto para o Replit.
3. Execute o projeto diretamente no Replit.

## Implantação com Netlify

1. Configure um novo site no Netlify.
2. Configure a construção do site para usar Docker.
3. Acesse a aplicação no link fornecido pelo Netlify.
