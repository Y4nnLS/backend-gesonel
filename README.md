# backend-gesonel

Backend robusto para gerenciamento, catalogação e consulta de arquivos de áudio, desenvolvido em **FastAPI** e **SQLAlchemy**, com persistência em **PostgreSQL**. O projeto foi pensado para servir como base de sistemas de pesquisa, bancos de dados de datasets de áudio, aplicações de machine learning e pipelines de processamento de sinais.

---

## ✨ Funcionalidades

- **CRUD completo** para arquivos de áudio (criação, listagem, consulta, atualização e remoção)
- **Filtros avançados** por dataset, rótulo de emoção, etc.
- **Validação de dados** com Pydantic (tipagem forte e validação automática)
- **Versionamento de API** (v1)
- **Integração com PostgreSQL** via SQLAlchemy ORM
- **Documentação automática** via Swagger/OpenAPI
- **Pronto para Docker/Docker Compose**
- **Estrutura modular** para fácil expansão (novos modelos, endpoints, autenticação, etc.)
- **Indexação** de campos relevantes para consultas rápidas
- **Separação clara** entre modelos, schemas, rotas e configuração de banco

---

## 🗂️ Estrutura do Projeto

```
backend-gesonel/
├── app/
│   ├── api/
│   │   ├── core/
│   │   │   └── db.py                # Configuração e conexão com o banco de dados
│   │   ├── models/
│   │   │   └── audio_file.py        # Modelo SQLAlchemy para arquivos de áudio
│   │   ├── schemas/
│   │   │   └── audio.py             # Schemas Pydantic para validação de dados
│   │   └── v1/
│   │       └── endpoints/
│   │           └── audios.py        # Endpoints REST para arquivos de áudio
│   ├── main.py                      # Inicialização da aplicação FastAPI
│   └── requirements.txt             # Dependências Python do app
├── db-stack/
│   └── .env                         # Variáveis de ambiente para banco e admin
├── requirements.txt                 # Dependências globais do projeto
└── .gitignore                       # Arquivos e pastas ignorados pelo git
```

---

## ⚙️ Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 13+
- (Opcional) Docker e Docker Compose para ambiente isolado

---

## 🚀 Instalação e Execução

### 1. Clone o repositório

```sh
git clone https://github.com/seuusuario/backend-gesonel.git
cd backend-gesonel
```

### 2. Crie e ative um ambiente virtual

```sh
python -m venv .venv
.venv\Scripts\activate   # Windows
# ou
source .venv/bin/activate  # Linux/Mac
```

### 3. Instale as dependências

```sh
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Edite o arquivo `db-stack/.env` com os dados do seu banco PostgreSQL e do pgAdmin:

```
POSTGRES_DB=appdb
POSTGRES_USER=appuser
POSTGRES_PASSWORD=secret

PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin123
```

### 5. (Opcional) Suba o banco de dados com Docker Compose

Crie um arquivo `docker-compose.yml` semelhante ao exemplo abaixo:

```yaml
version: '3.8'
services:
  db:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - ./db-data:/var/lib/postgresql/data
  pgadmin:
    image: dpage/pgadmin4
    restart: always
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "5050:80"
```

Suba os serviços:

```sh
docker-compose up -d
```

### 6. Execute as migrações do banco (caso utilize Alembic)

```sh
# alembic upgrade head
```

### 7. Inicie o servidor FastAPI

```sh
uvicorn app.main:app --reload
```

### 8. Acesse a documentação interativa

- [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

---

## 🛠️ Endpoints Principais

| Método | Rota                        | Descrição                                 |
|--------|-----------------------------|-------------------------------------------|
| GET    | `/v1/audios`                | Lista arquivos de áudio (com filtros)     |
| GET    | `/v1/audios/{audio_id}`     | Busca arquivo de áudio pelo ID            |
| POST   | `/v1/audios/upload`         | Cadastra um novo arquivo de áudio         |
| PUT    | `/v1/audios/{audio_id}`     | Atualiza os dados de um arquivo de áudio  |
| DELETE | `/v1/audios/{audio_id}`     | Remove um arquivo de áudio                |

### Parâmetros de Filtro

- `dataset`: Filtra por nome do dataset
- `emotion_label`: Filtra por rótulo de emoção
- `limit` e `offset`: Paginação dos resultados

### Exemplo de Payload para Upload

```json
{
  "rel_path": "datasets/cafe/0001.wav",
  "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
  "format": "wav",
  "duration_s": 3.5,
  "sample_rate": 16000,
  "channels": 1,
  "dataset": "cafe",
  "speaker_id": "spk01",
  "emotion_label": "feliz",
  "split": "train",
  "augment_pipeline": null
}
```

---

## 🧩 Expansão e Customização

- **Novos modelos:** Basta criar novos arquivos em `app/api/models/` e registrar os schemas/endpoints.
- **Autenticação:** Pode ser adicionada facilmente usando OAuth2, JWT ou integração com provedores externos.
- **Novos endpoints:** Siga o padrão de versionamento e modularização já implementado.
- **Testes:** Recomenda-se o uso de `pytest` para testes automatizados.

---

## 📝 Variáveis de Ambiente (.env)

Exemplo de configuração (`db-stack/.env`):

```
POSTGRES_DB=appdb
POSTGRES_USER=appuser
POSTGRES_PASSWORD=secret

PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin123
```

---

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b minha-feature`)
3. Commit suas alterações (`git commit -m 'feat: minha nova feature'`)
4. Faça push para a branch (`git push origin minha-feature`)
5. Abra um Pull Request

---

## 📄 Licença

MIT License

---

> Projeto desenvolvido para fins acadêmicos, científicos e de pesquisa. Sinta-se à vontade para contribuir, sugerir melhorias ou utilizar como base para seus