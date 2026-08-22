from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estoque.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            imagem TEXT,
            quantidade INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada','saida')),
            quantidade INTEGER NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)
    produtos_iniciais = [
        ("Coca-Cola", "coca_cola.png"),
        ("Pepsi", "pepsi.png"),
        ("Fanta", "fanta.png"),
    ]
    for nome, imagem in produtos_iniciais:
        conn.execute(
            "INSERT OR IGNORE INTO produtos (nome, imagem, quantidade) VALUES (?, ?, 0)",
            (nome, imagem)
        )
        conn.execute(
            "UPDATE produtos SET imagem = ? WHERE nome = ? AND (imagem IS NULL OR imagem = '')",
            (imagem, nome)
        )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()
    produtos = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()

    total_produtos = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    estoque_total = conn.execute("SELECT COALESCE(SUM(quantidade), 0) FROM produtos").fetchone()[0]
    total_entradas = conn.execute(
        "SELECT COUNT(*) FROM movimentos WHERE tipo = 'entrada'"
    ).fetchone()[0]
    total_saidas = conn.execute(
        "SELECT COUNT(*) FROM movimentos WHERE tipo = 'saida'"
    ).fetchone()[0]

    conn.close()
    return render_template(
        "index.html",
        produtos=produtos,
        total_produtos=total_produtos,
        estoque_total=estoque_total,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
    )


@app.route("/movimentar", methods=["POST"])
def movimentar():
    produto_id = request.form["produto_id"]
    tipo = request.form["tipo"]
    quantidade = int(request.form["quantidade"])

    conn = get_db()
    produto = conn.execute(
        "SELECT * FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()

    if tipo == "entrada":
        nova_quantidade = produto["quantidade"] + quantidade
    else:
        nova_quantidade = produto["quantidade"] - quantidade
        if nova_quantidade < 0:
            nova_quantidade = 0

    conn.execute(
        "UPDATE produtos SET quantidade = ? WHERE id = ?",
        (nova_quantidade, produto_id)
    )
    conn.execute(
        "INSERT INTO movimentos (produto_id, tipo, quantidade, data) VALUES (?, ?, ?, ?)",
        (produto_id, tipo, quantidade, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/produto/novo", methods=["GET", "POST"])
def novo_produto():
    if request.method == "POST":
        nome = request.form["nome"]
        imagem_file = request.files.get("imagem")
        nome_arquivo = None

        if imagem_file and imagem_file.filename:
            nome_arquivo = secure_filename(imagem_file.filename)
            imagem_file.save(os.path.join(app.config["UPLOAD_FOLDER"], nome_arquivo))

        conn = get_db()
        conn.execute(
            "INSERT INTO produtos (nome, imagem, quantidade) VALUES (?, ?, 0)",
            (nome, nome_arquivo)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    return render_template("add_product.html")


@app.route("/historico/<int:produto_id>")
def historico(produto_id):
    conn = get_db()
    produto = conn.execute(
        "SELECT * FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    movimentos = conn.execute(
        "SELECT * FROM movimentos WHERE produto_id = ? ORDER BY id DESC",
        (produto_id,)
    ).fetchall()
    conn.close()
    return render_template("historico.html", produto=produto, movimentos=movimentos)


@app.route("/historico/limpar", methods=["POST"])
def limpar_historico():
    conn = get_db()
    conn.execute("DELETE FROM movimentos")
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)