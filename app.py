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
app = Flask(__name__, static_folder='static', template_folder='templates')

# 🔹 Configurações
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'sua_chave_secreta_super_segura'

# 🔹 Ajustar corretamente o caminho do banco de dados
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'fornecedores.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔹 Configuração de diretórios de arquivos
UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted_files"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

# Criar diretórios se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# 🔹 Criar instância do banco de dados e migração
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 🔹 Modelos do Banco de Dados
class Fornecedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    codigo_contabil = db.Column(db.String(50), nullable=False)

class HistoricoUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

class ArquivoConvertido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(200), nullable=False)
    data_conversao = db.Column(db.DateTime, default=datetime.utcnow)

# 🔹 Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

# 🔹 Rotas do Sistema
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fornecedores')
def listar_fornecedores():
    fornecedores = Fornecedor.query.all()
    return render_template('fornecedores.html', fornecedores=fornecedores)

@app.route('/adicionar_fornecedor', methods=['POST'])
def adicionar_fornecedor():
    nome = request.form.get('nome')
    codigo_contabil = request.form.get('codigo_contabil')

    if not nome or not codigo_contabil:
        flash("Preencha todos os campos!", "danger")
        return redirect(url_for('listar_fornecedores'))

    novo_fornecedor = Fornecedor(nome=nome, codigo_contabil=codigo_contabil)

    try:
        db.session.add(novo_fornecedor)
        db.session.commit()
        flash("Fornecedor adicionado com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao adicionar fornecedor: {str(e)}", "danger")

    return redirect(url_for('listar_fornecedores'))

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

@app.route('/historico_uploads')
def historico_uploads():
    uploads = HistoricoUpload.query.order_by(HistoricoUpload.data_upload.desc()).all()
    return render_template('historico_uploads.html', uploads=uploads)



# 🔹 Importar e Converter Arquivo
@app.route('/importar_conversao', methods=['GET', 'POST'])
def importar_conversao():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("Nenhum arquivo enviado!", "danger")
            return redirect(url_for('importar_conversao'))

        file = request.files['file']
        if file.filename == '':
            flash("Nenhum arquivo selecionado!", "danger")
            return redirect(url_for('importar_conversao'))

        if file and file.filename.endswith('.xlsx'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Converter o arquivo
            converted_file = converter_arquivo(file_path)

            if converted_file:
                flash("Arquivo convertido com sucesso!", "success")
                return send_file(converted_file, as_attachment=True)
            else:
                flash("Erro ao converter o arquivo.", "danger")

    return render_template('importar_conversao.html')

# 🔹 Função para converter o arquivo
def converter_arquivo(input_path):
    try:
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], "arquivo_convertido.xlsx")

        # Carregar o arquivo base
        df = pd.read_excel(input_path, sheet_name="Table 1", header=None)

        # Identificar onde os dados começam
        start_idx = df[df.iloc[:, 0].astype(str).str.contains("Data", na=False, case=False)].index[0]
        df = df.iloc[start_idx:].reset_index(drop=True)

        # Definir cabeçalhos corretos
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)

        # Manter apenas as colunas relevantes
        df = df[['Data', 'NSU', 'Situação', 'Valor', 'Operação', 'Agência/Conta']]
        
        # Ajustar corretamente a correspondência do nome do fornecedor e dos valores
        df['Nome do Fornecedor'] = df['NSU'].shift(-1)

        # Ajustar valores
        df['Valor'] = df['Valor'].astype(str)
        df['Valor'] = df['Valor'].str.extract(r'([\d.,]+)')
        df['Valor'] = df['Valor'].str.replace(".", "", regex=True).str.replace(",", ".", regex=True)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

        # Ajustar formato da data
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime("%d-%m-%Y")

        # Adicionar colunas adicionais
        df["PAGAMENTO"] = 78
        df["HD"] = df["Nome do Fornecedor"].apply(
            lambda x: 10 if any(term in str(x).upper() for term in ["DARF", "FGTS", "INSS", "SEFAZ", "SECRETARIA FAZENDA"]) else 606
        )
        df["HC"] = 72

        # Criar código contábil baseado no nome do fornecedor (exemplo fictício)
        fornecedores = {"Fornecedor Exemplo": 12345, "Outro Fornecedor": 67890}
        df['Código Contábil'] = df['Nome do Fornecedor'].map(fornecedores)

        # Garantir que todas as colunas estejam na ordem correta
        ordered_columns = ["Data", "Nome do Fornecedor", "Valor", "PAGAMENTO", "HD", "HC", "Código Contábil"]
        df = df.reindex(columns=ordered_columns, fill_value=None)

        # Salvar o arquivo convertido
        df.to_excel(output_path, index=False)

        return output_path
    except Exception as e:
        print(f"❌ Erro durante a conversão: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True)

