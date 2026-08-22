from flask import Flask, abort, flash, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "estoque-dev-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estoque.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


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
    produto_id = request.form.get("produto_id")
    tipo = request.form.get("tipo")
    if not produto_id:
        abort(400)
    try:
        quantidade = int(request.form["quantidade"])
    except (KeyError, TypeError, ValueError):
        flash("Informe uma quantidade válida.", "erro")
        return redirect(url_for("index"))

    if quantidade < 1 or tipo not in {"entrada", "saida"}:
        flash("A quantidade deve ser maior que zero.", "erro")
        return redirect(url_for("index"))

    conn = get_db()
    produto = conn.execute(
        "SELECT * FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()

    if produto is None:
        conn.close()
        abort(404)

    if tipo == "entrada":
        nova_quantidade = produto["quantidade"] + quantidade
    else:
        if quantidade > produto["quantidade"]:
            conn.close()
            flash("A saída não pode ser maior que o estoque disponível.", "erro")
            return redirect(url_for("index"))
        nova_quantidade = produto["quantidade"] - quantidade

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
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Informe o nome do produto.", "erro")
            return render_template("add_product.html"), 400
        imagem_file = request.files.get("imagem")
        nome_arquivo = None

        if imagem_file and imagem_file.filename:
            if not allowed_image(imagem_file.filename):
                flash("Envie uma imagem PNG, JPG, JPEG, GIF ou WEBP.", "erro")
                return render_template("add_product.html"), 400
            nome_arquivo = secure_filename(imagem_file.filename)
            imagem_file.save(os.path.join(app.config["UPLOAD_FOLDER"], nome_arquivo))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO produtos (nome, imagem, quantidade) VALUES (?, ?, 0)",
                (nome, nome_arquivo)
            )
        except sqlite3.IntegrityError:
            conn.close()
            flash("Já existe um produto com esse nome.", "erro")
            return render_template("add_product.html"), 400
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
    if produto is None:
        conn.close()
        abort(404)
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)