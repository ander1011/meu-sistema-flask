import os
import pytest
from app import app, db, Fornecedor
from flask import url_for
from io import BytesIO

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Banco de testes em memória
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Criar tabelas no banco de testes
        yield client
        with app.app_context():
            db.drop_all()

# 1. Teste da Página Inicial
def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sistema de Gerenciamento" in response.data.decode("utf-8")

# 2. Teste de Upload de Arquivo Excel Válido
def test_upload_valid_file(client):
    data = {"file": (BytesIO(b"test_data"), "test.xlsx")}
    response = client.post("/importar_fornecedores", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code in [200, 302]


# 3. Teste de Upload de Arquivo Inválido
def test_upload_invalid_file_format(client):
    data = {"file": (BytesIO(b"test_data"), "test.txt")}
    response = client.post("/importar_fornecedores", data=data, content_type="multipart/form-data", follow_redirects=True)
    
    assert response.status_code in [200, 302] 
    assert "Formato de arquivo inválido" in response.get_data(as_text=True)  



# 4. Teste de Importação de Fornecedores
def test_importar_fornecedores(client):
    with app.app_context():
        # Criar fornecedor corretamente
        novo_fornecedor = Fornecedor(nome="Fornecedor Teste", cnpj="12345678000199", contato="contato@teste.com")
        db.session.add(novo_fornecedor)
        db.session.commit()
        db.session.refresh(novo_fornecedor)  # Garante que o ID foi gerado

    # Testa a listagem de fornecedores
    response = client.get("/fornecedores", follow_redirects=True)
    assert response.status_code == 200
    assert "Fornecedor Teste" in response.get_data(as_text=True)



# 5. Teste de Edição de Fornecedor
def test_editar_fornecedor(client):
    with app.app_context():
        fornecedor = Fornecedor(nome="Fornecedor Original", cnpj="98765432000100", contato="original@teste.com")
        db.session.add(fornecedor)
        db.session.commit()
        db.session.refresh(fornecedor)  # Adicione esta linha

    fornecedor_id = fornecedor.id
    assert fornecedor_id is not None

    data = {"nome": "Fornecedor Editado", "cnpj": "98765432000100", "contato": "editado@teste.com"}
    response = client.post(f"/editar/{fornecedor_id}", data=data, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        fornecedor_editado = Fornecedor.query.get(fornecedor_id)
        assert fornecedor_editado.nome == "Fornecedor Editado"


# 6. Teste de Exclusão de Fornecedor
def test_excluir_fornecedor(client):
    with app.app_context():
        fornecedor = Fornecedor(nome="Fornecedor Excluir", cnpj="11223344000155", contato="excluir@teste.com")
        db.session.add(fornecedor)
        db.session.commit()
        db.session.refresh(fornecedor)

    fornecedor_id = fornecedor.id
    response = client.get(f"/excluir/{fornecedor_id}", follow_redirects=True)
    assert response.status_code == 200

    # Verifica no banco se o fornecedor foi realmente excluído
    with app.app_context():
        fornecedor_excluido = db.session.get(Fornecedor, fornecedor_id)
        assert fornecedor_excluido is None



# 7. Teste de Exportação de Fornecedores
def test_exportar_fornecedores(client):
    response = client.get("/exportar_fornecedores")
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["Content-Type"]
