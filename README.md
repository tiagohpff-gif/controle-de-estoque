# Controle de Estoque

Painel administrativo em Flask para controlar produtos, entradas, saídas e histórico de movimentações.

## Rodar localmente

1. Crie um ambiente virtual e instale as dependências:

   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. Configure `DATABASE_URL` e `SECRET_KEY` no ambiente.
3. Inicie a aplicação:

   ```bash
   python app.py
   ```

Abra `http://127.0.0.1:5000`.

## Publicar no GitHub

O GitHub armazena o código, mas não executa o Flask. Depois de enviar este repositório para o GitHub, conecte-o a um serviço de hospedagem Python, como Render ou Railway.

Configuração do serviço:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Variáveis:** `DATABASE_URL` com a conexão do PostgreSQL/Supabase e `SECRET_KEY` com uma chave própria

O banco PostgreSQL deve existir antes do primeiro acesso. A aplicação cria as tabelas automaticamente quando `init_db()` é executado.