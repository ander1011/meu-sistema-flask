from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Fornecedor, HistoricoUpload
import pandas as pd
import os

main = Blueprint("main", __name__)

# Página inicial
@main.route('/')
def home():
    return render_template('base.html')

# Página de fornecedores
@main.route('/fornecedores')
def listar_fornecedores():
    fornecedores = Fornecedor.query.all()
    return render_template('fornecedores.html', fornecedores=fornecedores)

# Upload de Arquivos
@main.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)

            # Registrar no banco de dados
            novo_upload = HistoricoUpload(nome_arquivo=file.filename)
            db.session.add(novo_upload)
            db.session.commit()

            flash("Arquivo enviado com sucesso!", "success")
            return redirect(url_for('main.historico_uploads'))
    
    return render_template('upload.html')

# Histórico de Uploads
@main.route('/historico_uploads')
def historico_uploads():
    uploads = HistoricoUpload.query.order_by(HistoricoUpload.data_upload.desc()).all()
    return render_template('historico_uploads.html', uploads=uploads)
