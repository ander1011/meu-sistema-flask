from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import pandas as pd
import io
from datetime import datetime
from openpyxl import Workbook

# 🔹 Criar instância do Flask
app = Flask(__name__)

# 🔹 Configurações
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'sua_chave_secreta_super_segura'

# 🔹 Ajustar corretamente o caminho do banco de dados
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'fornecedores.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔹 Criar instância do banco de dados e migração
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 🔹 Importar modelos
class Fornecedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    codigo_contabil = db.Column(db.String(50), nullable=False)

class HistoricoUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Upload {self.nome_arquivo}>"

class ArquivoConvertido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(200), nullable=False)
    data_conversao = db.Column(db.DateTime, default=datetime.utcnow)

# 🔹 Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

# 🔹 Definir a pasta de upload de arquivos
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🔹 Rotas
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fornecedores')
def listar_fornecedores():
    fornecedores = Fornecedor.query.all()
    return render_template('fornecedores.html', fornecedores=fornecedores)

@app.route('/excluir_multiplo', methods=['GET'])
def excluir_multiplo():
    ids = request.args.get('ids')
    if not ids:
        flash("Nenhum fornecedor selecionado!", "danger")
        return redirect(url_for('listar_fornecedores'))

    id_list = [int(id) for id in ids.split(',')]
    try:
        Fornecedor.query.filter(Fornecedor.id.in_(id_list)).delete(synchronize_session=False)
        db.session.commit()
        flash("Fornecedores excluídos com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir fornecedores: {str(e)}", "danger")

    return redirect(url_for('listar_fornecedores'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    fornecedor = db.session.get(Fornecedor, id)
    if not fornecedor:
        flash("Fornecedor não encontrado!", "danger")
        return redirect(url_for('listar_fornecedores'))

    if request.method == 'POST':
        fornecedor.nome = request.form['nome']
        fornecedor.codigo_contabil = request.form['codigo_contabil']
        db.session.commit()
        flash("Fornecedor atualizado com sucesso!", "success")
        return redirect(url_for('listar_fornecedores'))

    return render_template('editar.html', fornecedor=fornecedor)

@app.route('/excluir/<int:id>')
def excluir(id):
    fornecedor = db.session.get(Fornecedor, id)
    if not fornecedor:
        flash("Fornecedor não encontrado!", "danger")
        return redirect(url_for('listar_fornecedores'))

    db.session.delete(fornecedor)
    db.session.commit()
    flash("Fornecedor excluído com sucesso!", "success")
    return redirect(url_for('listar_fornecedores'))

@app.route('/upload')
def upload_file():
    return render_template('upload.html')

@app.route('/exportar_fornecedores')
def exportar_fornecedores():
    fornecedores = Fornecedor.query.all()
    output = io.BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["ID", "Nome", "Código Contábil"])
    
    for fornecedor in fornecedores:
        sheet.append([fornecedor.id, fornecedor.nome, fornecedor.codigo_contabil])

    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="fornecedores.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/importar_fornecedores', methods=['POST'])
def importar_fornecedores():
    if 'file' not in request.files:
        flash("Nenhum arquivo enviado!", "danger")
        return redirect(url_for('listar_fornecedores'))

    file = request.files['file']
    if file.filename == '':
        flash("Nenhum arquivo selecionado!", "danger")
        return redirect(url_for('listar_fornecedores'))

    if file and file.filename.endswith('.xlsx'):
        try:
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                novo_fornecedor = Fornecedor(
                    nome=row["FORNECEDORES"],
                    codigo_contabil=row["Código Contábil"]
                )
                db.session.add(novo_fornecedor)

            historico = HistoricoUpload(nome_arquivo=file.filename)
            db.session.add(historico)
            db.session.commit()

            flash("Arquivo processado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao processar o arquivo: {str(e)}", "danger")
    else:
        flash("Formato de arquivo inválido.", "danger")

    return redirect(url_for('listar_fornecedores'))

@app.route('/historico_uploads')
def historico_uploads():
    uploads = HistoricoUpload.query.order_by(HistoricoUpload.data_upload.desc()).all()
    return render_template('historico_uploads.html', uploads=uploads)

@app.route('/arquivos_convertidos')
def arquivos_convertidos():
    arquivos = ArquivoConvertido.query.order_by(ArquivoConvertido.data_conversao.desc()).all()
    return render_template('arquivos_convertidos.html', arquivos=arquivos)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
