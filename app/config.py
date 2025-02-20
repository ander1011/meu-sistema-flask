import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Definir diretório base do projeto corretamente
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """ Configurações principais da aplicação """

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'fornecedores.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'sua_chave_secreta_super_segura'


# Criar instância do banco de dados
db = SQLAlchemy()

def create_app():
   
    app = Flask(__name__, instance_relative_config=False)
 
     """ Função para criar e configurar a aplicação Flask """
    app = Flask(__name__)

    # Carregar configurações do Flask a partir da classe Config
    app.config.from_object(Config)

    # Inicializar o banco de dados e o sistema de migração
    db.init_app(app)
    migrate = Migrate(app, db)

    # Importar rotas e registrar no app
    from routes import main
    app.register_blueprint(main)

    return app
