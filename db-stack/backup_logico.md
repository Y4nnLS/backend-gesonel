# README — Como compartilhar seu Postgres em Docker para outra máquina **sem perder os dados** (backup lógico)

Este guia mostra o caminho **recomendado** para migrar/compartilhar seu banco: **backup lógico com `pg_dump`** e  **restauração com `pg_restore`** . Funciona entre sistemas operacionais diferentes e até entre versões *majors* do Postgres (ex.: 15 → 16), desde que você **restaure** via dump (e não copie os arquivos brutos do data dir).

---

## 📦 O que vamos transferir

* Arquivos do projeto:
  * `docker-compose.yml`
  * `.env` (com **usuário/senha** do Postgres e do pgAdmin —  *não comite em Git público* )
* **Dump lógico** do banco:
  * `backups/appdb.dump` (formato  **custom** : `-F c`)

> Exemplo de serviço no `docker-compose.yml`:
>
> * Container do Postgres: **`pg-db`**
> * DB: **`appdb`** | Usuário: **`appuser`** | Senha: **`secret`**

---

## 🧰 Pré-requisitos

* Docker e Docker Compose v2 instalados nas duas máquinas
* Stack do Postgres subindo com `docker compose up -d`
* Acesso ao terminal:
  * **Windows** : PowerShell
  * **macOS/Linux** : bash/zsh

---

## 🗂️ Estrutura sugerida de pastas

```
db-stack/
├─ docker-compose.yml
├─ .env
├─ backups/
│  └─ appdb.dump         # será criado por você no passo de backup
└─ (volumes Docker criados automaticamente)
```

Crie a pasta de backups (se ainda não existir):

**Windows (PowerShell)**

```powershell
mkdir .\backups -Force
```

**macOS/Linux**

```bash
mkdir -p ./backups
```

---

## 1) 📤 Fazer o **backup lógico** na máquina origem

> O comando roda **dentro do container** `pg-db` e grava um `.dump` em `/tmp`. Depois copiamos para a pasta `backups/` do host.

**Windows (PowerShell)**

```powershell
docker exec -t pg-db pg_dump -U appuser -d appdb -F c -f /tmp/appdb.dump
docker cp pg-db:/tmp/appdb.dump .\db-stack\backups\appdb.dump
```

**macOS/Linux**

```bash
docker exec -t pg-db pg_dump -U appuser -d appdb -F c -f /tmp/appdb.dump
docker cp pg-db:/tmp/appdb.dump ./db-stack/backups/appdb.dump
```

> Por que `-F c` (formato custom)?
>
> Restauração mais rápida, permite paralelização e opções como `--clean`.

---

## 2) 🚚 Levar para a máquina destino

Copie os arquivos abaixo para a nova máquina (via pendrive, rede, Git privado, etc.):

```
db-stack/
├─ docker-compose.yml
├─ .env
└─ backups/
   └─ appdb.dump
```

> Ajuste o `.env` da nova máquina se quiser  **alterar senha/usuário/DB** .

---

## 3) 📥 Restaurar na máquina destino

1. Suba o Postgres  **vazio** :
   ```bash
   docker compose up -d
   ```
2. Copie o dump para dentro do container:
   * **Windows**
     ```powershell
     docker cp .\backups\appdb.dump pg-db:/tmp/appdb.dump
     ```
   * **macOS/Linux**
     ```bash
     docker cp ./backups/appdb.dump pg-db:/tmp/appdb.dump
     ```
3. Restaure o banco:
   ```bash
   docker exec -t pg-db pg_restore -U appuser -d appdb --clean --if-exists /tmp/appdb.dump
   ```

> O `--clean --if-exists` derruba e recria objetos se já existirem.

### 💡 Quero criar o banco durante a restauração

Se o banco `appdb` **não existe** e você quer criá-lo no restore:

```bash
docker exec -t pg-db pg_restore -U appuser -d postgres --create /tmp/appdb.dump
```

> Neste caso, o dump precisa **conter o CREATE DATABASE** (normalmente contém quando você usa `pg_dump` no DB inteiro). Depois conecte-se ao DB recém-criado.

---

## 4) ✅ Verificar

* Logs do Postgres:
  ```bash
  docker compose logs -f pg-db
  ```
* Testar conexão (por ex., com `psql` dentro do container):
  ```bash
  docker exec -it pg-db psql -U appuser -d appdb -c "\dt"
  ```
* Abrir **pgAdmin** (se você usa no compose), registrar servidor e conferir tabelas.

---

## 🔐 Dicas de segurança

* **Nunca** publique `.env` com senhas em repositórios públicos.
* Gere senhas fortes na máquina destino.
* Se publicar a porta `5432`, restrinja o acesso por firewall/SG ou use rede privada/VPN.

---

## 🧪 Troubleshooting (erros comuns)

**“FATAL: database 'appdb' does not exist”**

→ Crie o DB (`createdb`) ou restaure com `pg_restore ... -d postgres --create`.

**“permission denied” ao rodar pg_dump/restore**

→ Verifique usuário (`-U appuser`) e privilégios. Use o usuário com permissão para todos os objetos.

**“pg-db” não encontrado**

→ Confirme o **nome do serviço** no `docker-compose.yml` (`services.db.container_name` pode ser outro).

Ajuste os comandos `docker exec/cp` para o nome correto.

**Versões diferentes do Postgres**

→ O método com **dump lógico** é justamente para cruzar versões. Se tentou copiar **arquivos do volume** e deu erro, volte para este método.

---

## 🧾 FAQ

**Posso automatizar o backup?**

Sim. Crie um script/cron (ou um Workflow) que rode `pg_dump` e copie o arquivo para `backups/` com carimbo de data.

**Preciso levar o volume `pgadmin`?**

Não necessariamente. Ele guarda *apenas* suas conexões salvas no pgAdmin. Na nova máquina você pode registrar o servidor de novo em 1 minuto.

**E se eu quiser migrar mais de um banco?**

Rode `pg_dump` para cada DB, gere múltiplos `.dump` e restaure cada um na máquina destino.

---

## 📝 Apêndice — Comandos equivalentes (tudo em uma linha)

**Backup (origem):**

```bash
docker exec -t pg-db pg_dump -U appuser -d appdb -F c -f /tmp/appdb.dump && \
docker cp pg-db:/tmp/appdb.dump ./backups/appdb.dump
```

**Restauração (destino):**

```bash
docker compose up -d && \
docker cp ./backups/appdb.dump pg-db:/tmp/appdb.dump && \
docker exec -t pg-db pg_restore -U appuser -d appdb --clean --if-exists /tmp/appdb.dump
```

---

Pronto! Com esse fluxo você compartilha/migra seu banco **com segurança** e  **sem dor de cabeça** . Se quiser, eu acrescento uma seção de **“restore parcial”** (apenas um schema/tabela) e outra de **“backup agendado”** com exemplos para PowerShell e cron.



comando para rodar o ingest_audio
$env:DATABASE_URL="postgresql://appuser:secret@localhost:5432/appdb"
python db-stack/tools/ingest_audio.py --audio-root "db-stack/audios" --recursive --infer-from-path 

adicionar a linha abaixo para simular a ingestão sem alterar o banco.
--dry-run