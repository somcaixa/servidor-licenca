from flask import Flask, request, jsonify
import os
import psycopg2
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)

SECRET_KEY = "TROQUE_POR_UMA_CHAVE_GRANDE_E_FORTE_2026"
DATABASE_URL = os.environ.get("DATABASE_URL")

# ----------------------------
# CONEXÃO COM POSTGRESQL
# ----------------------------
def conectar():
    return psycopg2.connect(DATABASE_URL)

# ----------------------------
# CRIAR TABELAS SE NÃO EXISTIREM
# ----------------------------
def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS licencas (
        chave TEXT PRIMARY KEY,
        usada BOOLEAN DEFAULT FALSE,
        hardware_id TEXT,
        expira_em DATE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS backups (
        id SERIAL PRIMARY KEY,
        hardware_id TEXT,
        arquivo BYTEA,
        data TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

# ----------------------------
# GERAR CHAVES (ROTA ADMIN)
# ----------------------------
@app.route("/gerar", methods=["POST"])
def gerar_chaves():
    senha_admin = request.json.get("senha")

    if senha_admin != "ADMIN_SUPER_2026":
        return jsonify({"status": "erro", "msg": "Não autorizado"})

    conn = conectar()
    c = conn.cursor()

    chaves_geradas = []

    for _ in range(10):
        chave = secrets.token_hex(16)
        c.execute("INSERT INTO licencas (chave) VALUES (%s)", (chave,))
        chaves_geradas.append(chave)

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "chaves": chaves_geradas
    })

# ----------------------------
# ATIVAÇÃO
# ----------------------------
@app.route("/ativar", methods=["POST"])
def ativar():
    dados = request.json
    chave = dados.get("chave")
    hardware = dados.get("hardware")

    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT usada FROM licencas WHERE chave=%s", (chave,))
    resultado = c.fetchone()

    if not resultado:
        conn.close()
        return jsonify({"status": "erro", "msg": "Chave inválida"})

    if resultado[0]:
        conn.close()
        return jsonify({"status": "erro", "msg": "Chave já utilizada"})

    expira = datetime.now() + timedelta(days=30)

    c.execute("""
        UPDATE licencas
        SET usada=TRUE, hardware_id=%s, expira_em=%s
        WHERE chave=%s
    """, (hardware, expira.date(), chave))

    conn.commit()
    conn.close()

    assinatura = hmac.new(
        SECRET_KEY.encode(),
        f"{hardware}{expira.date()}".encode(),
        hashlib.sha256
    ).hexdigest()

    return jsonify({
        "status": "ok",
        "expira": str(expira.date()),
        "assinatura": assinatura
    })

# ----------------------------
# BACKUP
# ----------------------------
@app.route("/backup", methods=["POST"])
def backup():
    hardware = request.form.get("hardware")
    arquivo = request.files["arquivo"].read()

    conn = conectar()
    c = conn.cursor()

    c.execute("""
        INSERT INTO backups (hardware_id, arquivo, data)
        VALUES (%s, %s, %s)
    """, (hardware, psycopg2.Binary(arquivo), datetime.now()))

    conn.commit()
    conn.close()

    return "Backup salvo"

# ----------------------------
# RESTAURAR BACKUP
# ----------------------------
@app.route("/restaurar/<hardware>")
def restaurar(hardware):
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        SELECT arquivo FROM backups
        WHERE hardware_id=%s
        ORDER BY data DESC
        LIMIT 1
    """, (hardware,))

    resultado = c.fetchone()
    conn.close()

    if not resultado:
        return "Sem backup"

    return resultado[0]

# ----------------------------
# RENDER START
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
