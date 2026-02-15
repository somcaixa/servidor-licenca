from flask import Flask, request, jsonify
import os
import psycopg2
import hashlib
import hmac
from datetime import datetime, timedelta

app = Flask(__name__)

SECRET_KEY = "SUA_CHAVE_ULTRA_SECRETA_2026"
DATABASE_URL = os.environ.get("DATABASE_URL")

def conectar():
    return psycopg2.connect(DATABASE_URL)

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
        return jsonify({"status": "erro", "msg": "Chave inválida"})

    if resultado[0]:
        return jsonify({"status": "erro", "msg": "Chave já utilizada"})

    expira = datetime.now() + timedelta(days=30)

    c.execute("""
        UPDATE licencas
        SET usada=TRUE, hardware_id=%s, expira_em=%s
        WHERE chave=%s
    """, (hardware, expira, chave))

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