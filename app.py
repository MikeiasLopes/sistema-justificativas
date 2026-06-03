from flask import Flask, render_template, request, redirect, send_file, session
import sqlite3
from openpyxl import Workbook

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime
import base64
import io

app = Flask(__name__)
app.secret_key = "chave_secreta_do_sistema"


def criar_banco():
    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS justificativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT,

            nome TEXT,
            matricula TEXT,
            data TEXT,

            prefixo_veiculo TEXT,
            linha_escala TEXT,

            inicio_jornada TEXT,
            final_jornada TEXT,
            inicio_intervalo TEXT,
            final_intervalo TEXT,

            justificativa TEXT,
            status TEXT DEFAULT 'Pendente',

            nome_responsavel TEXT,
            chapa_responsavel TEXT,

            assinatura TEXT,
            assinatura_responsavel TEXT,

            observacao_rh TEXT,
            usuario_rh TEXT,
            data_acao TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha TEXT,
            perfil TEXT
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (
            nome,
            usuario,
            senha,
            perfil
        )
        VALUES (
            'Administrador',
            'admin',
            '123456',
            'admin'
        )
    """)

    conexao.commit()
    conexao.close()

@app.route("/")
def formulario():
    return render_template("formulario.html")


@app.route("/enviar", methods=["POST"])
def enviar():
    nome = request.form["nome"]
    matricula = request.form["matricula"]
    data = request.form["data"]

    prefixo_veiculo = request.form["prefixo_veiculo"]
    linha_escala = request.form["linha_escala"]

    inicio_jornada = request.form["inicio_jornada"]
    final_jornada = request.form["final_jornada"]
    inicio_intervalo = request.form["inicio_intervalo"]
    final_intervalo = request.form["final_intervalo"]

    justificativa = request.form["justificativa"]

    nome_responsavel = request.form["nome_responsavel"]
    chapa_responsavel = request.form["chapa_responsavel"]

    assinatura = request.form["assinatura"]
    assinatura_responsavel = request.form["assinatura_responsavel"]

    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    data_atual = datetime.now().strftime("%Y%m%d")

    cursor.execute("SELECT COUNT(*) FROM justificativas")
    quantidade = cursor.fetchone()[0] + 1

    protocolo = f"JH-{data_atual}-{quantidade:05d}"

    cursor.execute("""
        INSERT INTO justificativas (
            protocolo,
            nome,
            matricula,
            data,
            prefixo_veiculo,
            linha_escala,
            inicio_jornada,
            final_jornada,
            inicio_intervalo,
            final_intervalo,
            justificativa,
            status,
            nome_responsavel,
            chapa_responsavel,
            assinatura,
            assinatura_responsavel
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        protocolo,
        nome,
        matricula,
        data,
        prefixo_veiculo,
        linha_escala,
        inicio_jornada,
        final_jornada,
        inicio_intervalo,
        final_intervalo,
        justificativa,
        "Pendente",
        nome_responsavel,
        chapa_responsavel,
        assinatura,
        assinatura_responsavel
    ))

    conexao.commit()
    conexao.close()

    return render_template("sucesso.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conexao = sqlite3.connect("justificativas.db")
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT
                id,
                nome,
                usuario,
                perfil
            FROM usuarios
            WHERE usuario = ?
            AND senha = ?
        """, (usuario, senha))

        usuario_logado = cursor.fetchone()

        conexao.close()

        if usuario_logado:

            session["logado"] = True
            session["usuario_id"] = usuario_logado[0]
            session["nome_usuario"] = usuario_logado[1]
            session["usuario"] = usuario_logado[2]
            session["perfil"] = usuario_logado[3]

            return redirect("/admin")

        return "Usuário ou senha inválidos"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin")
def admin():
    if not session.get("logado"):
        return redirect("/login")

    pesquisa = request.args.get("pesquisa", "")
    status = request.args.get("status", "")
    data_inicial = request.args.get("data_inicial", "")
    data_final = request.args.get("data_final", "")

    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    query = """
        SELECT *
        FROM justificativas
        WHERE 1=1
    """

    parametros = []

    if pesquisa:
        query += """
            AND (
                nome LIKE ?
                OR matricula LIKE ?
                OR nome_responsavel LIKE ?
                OR chapa_responsavel LIKE ?
                OR prefixo_veiculo LIKE ?
                OR linha_escala LIKE ?
            )
        """
        parametros.extend([
            f"%{pesquisa}%",
            f"%{pesquisa}%",
            f"%{pesquisa}%",
            f"%{pesquisa}%",
            f"%{pesquisa}%",
            f"%{pesquisa}%"
        ])

    if status:
        query += " AND status = ?"
        parametros.append(status)

    if data_inicial:
        query += " AND data >= ?"
        parametros.append(data_inicial)

    if data_final:
        query += " AND data <= ?"
        parametros.append(data_final)

    query += " ORDER BY id DESC"

    cursor.execute(query, parametros)
    registros = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM justificativas")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM justificativas WHERE status = 'Pendente'")
    pendentes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM justificativas WHERE status = 'Aprovado'")
    aprovadas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM justificativas WHERE status = 'Reprovado'")
    reprovadas = cursor.fetchone()[0]

    if total > 0:
        taxa_aprovacao = round((aprovadas / total) * 100, 2)
    else:
        taxa_aprovacao = 0

    conexao.close()

    return render_template(
        "admin.html",
        registros=registros,
        total=total,
        pendentes=pendentes,
        aprovadas=aprovadas,
        reprovadas=reprovadas,
        taxa_aprovacao=taxa_aprovacao,
        pesquisa=pesquisa,
        status=status,
        data_inicial=data_inicial,
        data_final=data_final
    )




@app.route("/aprovar/<int:id>", methods=["GET", "POST"])
def aprovar(id):

    if not session.get("logado"):
        return redirect("/login")

    if request.method == "POST":

        observacao = request.form["observacao"]
        usuario_logado = session.get("nome_usuario", "RH")

        conexao = sqlite3.connect("justificativas.db")
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE justificativas
            SET
                status = 'Aprovado',
                observacao_rh = ?,
                usuario_rh = ?,
                data_acao = datetime('now','localtime')
            WHERE id = ?
        """, (observacao, usuario_logado, id))

        conexao.commit()
        conexao.close()

        return redirect("/admin")

    return render_template(
        "observacao.html",
        titulo="Aprovar Justificativa",
        acao="Aprovar"
    )


@app.route("/reprovar/<int:id>", methods=["GET", "POST"])
def reprovar(id):

    if not session.get("logado"):
        return redirect("/login")

    if request.method == "POST":

        observacao = request.form["observacao"]
        usuario_logado = session.get("nome_usuario", "RH")

        conexao = sqlite3.connect("justificativas.db")
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE justificativas
            SET
                status = 'Reprovado',
                observacao_rh = ?,
                usuario_rh = ?,
                data_acao = datetime('now','localtime')
            WHERE id = ?
        """, (observacao, usuario_logado, id))

        conexao.commit()
        conexao.close()

        return redirect("/admin")

    return render_template(
        "observacao.html",
        titulo="Reprovar Justificativa",
        acao="Reprovar"
    )

@app.route("/exportar_excel")
def exportar_excel():
    if not session.get("logado"):
        return redirect("/login")

    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT 
            id,
            nome,
            matricula,
            data,
            inicio_jornada,
            final_jornada,
            inicio_intervalo,
            final_intervalo,
            justificativa,
            status,
            nome_responsavel,
            chapa_responsavel
        FROM justificativas
        ORDER BY id DESC
    """)

    dados = cursor.fetchall()
    conexao.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Justificativas"

    ws.append([
        "ID",
        "Nome do Motorista",
        "Matrícula / Chapa",
        "Data",
        "Início da Jornada",
        "Final da Jornada",
        "Início do Intervalo",
        "Final do Intervalo",
        "Justificativa",
        "Status",
        "Nome do Responsável",
        "Chapa do Responsável"
    ])

    for linha in dados:
        ws.append(linha)

    arquivo = "justificativas.xlsx"
    wb.save(arquivo)

    return send_file(arquivo, as_attachment=True)

@app.route("/pdf/<int:id>")
def gerar_pdf(id):

    if not session.get("logado"):
        return redirect("/login")

    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM justificativas
        WHERE id = ?
    """, (id,))

    registro = cursor.fetchone()
    conexao.close()

    if registro is None:
        return "Registro não encontrado"

    arquivo = f"justificativa_{id}.pdf"

    pdf = canvas.Canvas(arquivo, pagesize=A4)
    largura, altura = A4

    cor_azul = (0.05, 0.18, 0.42)
    cor_azul_claro = (0.12, 0.34, 0.62)

    def texto_quebrado(texto, x, y, limite=90, tamanho=8):
        texto = str(texto or "")
        palavras = texto.split()
        linha = ""

        pdf.setFont("Helvetica", tamanho)

        for palavra in palavras:
            teste = linha + " " + palavra if linha else palavra

            if len(teste) <= limite:
                linha = teste
            else:
                pdf.drawString(x, y, linha)
                y -= 11
                linha = palavra

        if linha:
            pdf.drawString(x, y, linha)
            y -= 11

        return y

    def titulo_secao(texto, y):
        pdf.setFillColorRGB(*cor_azul)
        pdf.roundRect(30, y - 5, 535, 20, 4, fill=1, stroke=0)

        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(42, y, texto)

        pdf.setFillColorRGB(0, 0, 0)
        return y - 26

    def campo(label, valor, x, y, deslocamento=105):
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x, y, f"{label}:")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + deslocamento, y, str(valor or ""))
        return y - 13

    def assinatura(base64_img, x, y, titulo):
        pdf.setFillColorRGB(1, 1, 1)
        pdf.roundRect(x, y, 250, 90, 6, stroke=1, fill=0)

        try:
            if base64_img:
                imagem = base64.b64decode(base64_img.split(",")[1])

                pdf.drawImage(
                    ImageReader(io.BytesIO(imagem)),
                    x + 15,
                    y + 12,
                    width=220,
                    height=65,
                    mask="auto"
                )
            else:
                pdf.setFont("Helvetica", 8)
                pdf.drawCentredString(x + 125, y + 42, "Sem assinatura")

        except:
            pdf.line(x + 15, y - 14, x + 235, y - 14)

            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawCentredString(x + 125, y - 27, titulo)

            pdf.setFont("Helvetica", 7)

            if "Motorista" in titulo:
                pdf.drawCentredString(
                    x + 125,
                    y - 39,
                    str(registro[2] or "")
                )
            else:
                pdf.drawCentredString(
                    x + 125,
                    y - 39,
                    str(registro[13] or "")
                )

    # CABEÇALHO
    pdf.setFillColorRGB(*cor_azul)
    pdf.rect(0, 765, largura, 77, fill=1, stroke=0)

    pdf.setFillColorRGB(*cor_azul_claro)
    pdf.rect(0, 765, largura, 6, fill=1, stroke=0)

    # LOGO À ESQUERDA
    try:
        pdf.drawImage(
            "static/logo_vrt.jpg",
            3,  # margem esquerda
            782,
            width=230,
            height=50,
            preserveAspectRatio=True,
            mask="auto"
        )
    except Exception as erro:
        print("Erro ao carregar logo:", erro)

    # Área à direita da logo
    inicio_area = 250
    fim_area = 595  # largura da página A4
    centro = (inicio_area + fim_area) / 2

    pdf.setFillColorRGB(1, 1, 1)

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(
        centro,
        812,
        "JUSTIFICATIVA DIGITAL"
    )

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        centro,
        794,
        "Controle de Ajuste de Jornada"
    )

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(
        centro,
        780,
        "Documento gerado eletronicamente pelo sistema interno"
    )

    pdf.setFillColorRGB(0, 0, 0)

    # STATUS
    status = registro[12] or "Pendente"

    if status == "Aprovado":
        cor_status = (0, 0.55, 0)
    elif status == "Reprovado":
        cor_status = (0.75, 0, 0)
    else:
        cor_status = (0.85, 0.55, 0)

    pdf.setFillColorRGB(*cor_status)
    pdf.setStrokeColorRGB(*cor_status)

    pdf.roundRect(
        420,
        724,
        130,
        30,
        5,
        stroke=1,
        fill=0
    )

    pdf.setFont("Helvetica-Bold", 20)

    pdf.drawCentredString(
        485,
        724,
        status.upper()
    )

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setStrokeColorRGB(0, 0, 0)



    # PROTOCOLO
    y = 745

    pdf.setFillColorRGB(0.92, 0.92, 0.92)
    pdf.roundRect(30, y - 8, 270, 25, 4, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(42, y, f"PROTOCOLO: {registro[1]}")

    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(
        555,
        722,
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    y = 705

    # MOTORISTA
    y = titulo_secao("INFORMAÇÕES DO MOTORISTA", y)

    pdf.roundRect(30, y - 76, 535, 86, 6, stroke=1, fill=0)

    y = campo("Nome", registro[2], 45, y - 12)
    y = campo("Matrícula / Chapa", registro[3], 45, y)
    y = campo("Data", registro[4], 45, y)
    y = campo("Prefixo do Veículo", registro[5], 45, y)
    y = campo("Linha / Escala", registro[6], 45, y)

    y -= 16

    # JORNADA
    y = titulo_secao("REGISTRO DA JORNADA", y)

    pdf.roundRect(30, y - 48, 535, 58, 6, stroke=1, fill=0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(45, y - 15, "Início da Jornada:")
    pdf.drawString(315, y - 15, "Final da Jornada:")
    pdf.drawString(45, y - 35, "Início do Intervalo:")
    pdf.drawString(315, y - 35, "Final do Intervalo:")

    pdf.setFont("Helvetica", 8)
    pdf.drawString(160, y - 15, str(registro[7] or ""))
    pdf.drawString(430, y - 15, str(registro[8] or ""))
    pdf.drawString(160, y - 35, str(registro[9] or ""))
    pdf.drawString(430, y - 35, str(registro[10] or ""))

    y -= 73

    # JUSTIFICATIVA
    y = titulo_secao("JUSTIFICATIVA APRESENTADA", y)

    pdf.setFillColorRGB(0.97, 0.97, 0.97)
    pdf.roundRect(30, y - 72, 535, 82, 6, fill=1, stroke=1)

    pdf.setFillColorRGB(0, 0, 0)
    texto_quebrado(registro[11], 45, y - 15, 95, 8.5)

    y -= 100

    # RESPONSÁVEL E RH
    y = titulo_secao("ANÁLISE E VALIDAÇÃO", y)

    pdf.roundRect(30, y - 86, 260, 96, 6, stroke=1, fill=0)
    pdf.roundRect(305, y - 86, 260, 96, 6, stroke=1, fill=0)

    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(45, y - 15, "Responsável pelo Envio")
    pdf.drawString(320, y - 15, "Validação do RH")

    campo("Nome", registro[13], 45, y - 35, 70)
    campo("Chapa", registro[14], 45, y - 50, 70)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(320, y - 35, "Status:")

    if status == "Aprovado":
        pdf.setFillColorRGB(0, 0.55, 0)
    elif status == "Reprovado":
        pdf.setFillColorRGB(0.75, 0, 0)
    else:
        pdf.setFillColorRGB(0.85, 0.55, 0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(385, y - 35, status)

    pdf.setFillColorRGB(0, 0, 0)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(320, y - 50, "Usuário RH:")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(385, y - 50, str(registro[18] or ""))

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(320, y - 65, "Data Ação:")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(385, y - 65, str(registro[19] or ""))

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(45, y - 68, "Observação RH:")
    texto_quebrado(registro[17], 130, y - 68, 38, 8)

    y -= 113

    # ASSINATURAS
    y = titulo_secao("ASSINATURAS DIGITAIS", y)

    assinatura_y = y - 92

    assinatura(
        registro[15],
        30,
        assinatura_y,
        "Assinatura do Motorista"
    )

    assinatura(
        registro[16],
        315,
        assinatura_y,
        "Assinatura do Responsável"
    )

    # RODAPÉ
    pdf.setStrokeColorRGB(0.7, 0.7, 0.7)
    pdf.line(30, 45, 565, 45)

    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    pdf.setFont("Helvetica-Oblique", 7)
    pdf.drawString(
        30,
        32,
        "Documento válido eletronicamente. Gerado pelo Sistema de Justificativas de Horas."
    )

    pdf.drawCentredString(
        297,
        20,
        "Página 1 de 1"
    )

    pdf.drawRightString(
        565,
        32,
        f"Protocolo: {registro[1]}"
    )

    pdf.save()

    return send_file(
        arquivo,
        as_attachment=True
    )

@app.route("/excluir/<int:id>")
def excluir(id):
    if not session.get("logado"):
        return redirect("/login")

    conexao = sqlite3.connect("justificativas.db")
    cursor = conexao.cursor()

    cursor.execute("""
        DELETE FROM justificativas
        WHERE id = ?
    """, (id,))

    conexao.commit()
    conexao.close()

    return redirect("/admin")

if __name__ == "__main__":
    criar_banco()

    app.run(debug=True)