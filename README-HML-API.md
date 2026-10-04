# Cabana Gestão — HML API / PostgreSQL

Pacote de publicação da **API V3 HML**, sem alterar a interface homologada atual e sem mexer nos dados do PostgreSQL já criado.

## O que este pacote faz

- publica `ghcr.io/madsonpersonal-max/cabana-gestao-api:hml` via GitHub Actions;
- conecta a API ao PostgreSQL `cabana_gestao_hml`;
- usa os três secrets já criados no Portainer:
  - `dp_cabana_hml_db_password`
  - `dp_cabana_hml_jwt_secret`
  - `dp_cabana_hml_admin_password`
- cria automaticamente o usuário HML `admin` na primeira inicialização;
- disponibiliza `/api/health` e `/api/ready`;
- disponibiliza login e endpoints iniciais de colaboradores, fechamento e auditoria;
- não publica a porta 8000 na internet;
- mantém o banco no volume persistente já existente.

## IMPORTANTE

Não substituir ainda a interface web homologada. Este passo é somente para validar **API + PostgreSQL + secrets + persistência**.

Também não remover o volume `dp-cabana-hml_dp_cabana_hml_db`.

## Passo 1 — GitHub

Copiar para o repositório `madsonpersonal-max/cabana-gestao-dp`:

- `api/`
- `db/001_init.sql` (somente referência para futuras inicializações/migrações; não será reaplicado no volume já inicializado)
- `.github/workflows/build-hml-api.yml`

O GitHub Actions usa `GITHUB_TOKEN` com `packages: write` para publicar a imagem no GHCR.

## Passo 2 — Executar Actions

No GitHub:

`Actions` → `Build and publish Cabana Gestão API HML` → `Run workflow`

Ao concluir, deve existir a imagem:

`ghcr.io/madsonpersonal-max/cabana-gestao-api:hml`

## Passo 3 — Atualizar o stack HML no Portainer

Manter o nome do stack: `dp-cabana-hml`.

Usar o conteúdo de `stack-hml-api.yml` no Web Editor e atualizar o stack.

O serviço `db` continua usando o mesmo volume externo e os mesmos secrets. O serviço `api` será adicionado à rede interna.

## Passo 4 — Validação

No serviço `dp-cabana-hml_api`:

- `1/1` replica;
- estado `running`;
- healthcheck sem erro;
- logs sem `database unavailable`;
- `/api/ready` respondendo `status=ready` internamente.

Depois disso, o próximo passo será integrar a interface homologada ao `/api`, módulo por módulo. Não migrar todos os módulos de uma vez.
