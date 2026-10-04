import base64
import hashlib
import hmac
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import jwt
import psycopg
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.rows import dict_row
from pydantic import BaseModel

APP_VERSION = "3.0.0-hml-api-1"

app = FastAPI(
    title="Cabana Gestão API",
    version=APP_VERSION
)

security = HTTPBearer(auto_error=False)


def read_secret(env_name: str, default: str | None = None) -> str | None:
    file_path = os.getenv(env_name)

    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            raise RuntimeError(
                f"Secret file not found: {file_path}"
            )

    return os.getenv(
        env_name.replace("_FILE", ""),
        default
    )


DB_PASSWORD = read_secret("DB_PASSWORD_FILE")
JWT_SECRET = read_secret("JWT_SECRET_FILE")
ADMIN_PASSWORD = read_secret("ADMIN_PASSWORD_FILE")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "cabana_gestao_hml")
DB_USER = os.getenv("DB_USER", "cabana")

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = int(
    os.getenv("JWT_EXPIRES_HOURS", "8")
)


def database_url() -> str:
    if not DB_PASSWORD:
        raise RuntimeError(
            "DB_PASSWORD não configurada"
        )

    return (
        f"postgresql://"
        f"{quote(DB_USER)}:"
        f"{quote(DB_PASSWORD)}@"
        f"{DB_HOST}:"
        f"{DB_PORT}/"
        f"{quote(DB_NAME)}"
    )


def conn():
    return psycopg.connect(
        database_url(),
        row_factory=dict_row
    )


def hash_password(
    password: str,
    salt: bytes | None = None
) -> str:

    salt = salt or os.urandom(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1
    )

    return (
        "scrypt$16384$8$1$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(
    password: str,
    encoded: str
) -> bool:

    try:
        scheme, n, r, p, salt_b64, digest_b64 = (
            encoded.split("$", 5)
        )

        if scheme != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(
            salt_b64.encode()
        )

        expected = base64.urlsafe_b64decode(
            digest_b64.encode()
        )

        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p)
        )

        return hmac.compare_digest(
            actual,
            expected
        )

    except Exception:
        return False


def ensure_admin():

    if not ADMIN_PASSWORD:
        raise RuntimeError(
            "ADMIN_PASSWORD não configurada"
        )

    with conn() as c:

        row = c.execute(
            "select id from users where username='admin'"
        ).fetchone()

        if row:
            return

        c.execute(
            """
            insert into users
            (name, username, password_hash, role)
            values (%s, %s, %s, %s)
            """,
            (
                "Administrador HML",
                "admin",
                hash_password(ADMIN_PASSWORD),
                "ADMIN"
            )
        )

        c.commit()


@app.on_event("startup")
def startup():

    with conn() as c:
        c.execute("select 1")

    ensure_admin()


@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "service": "cabana-gestao-api",
        "version": APP_VERSION
    }


@app.get("/api/ready")
def ready():

    try:

        with conn() as c:
            c.execute("select 1")

        return {
            "status": "ready",
            "database": "ok"
        }

    except Exception:

        raise HTTPException(
            status_code=503,
            detail="database unavailable"
        )


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(item: LoginIn):

    with conn() as c:

        user = c.execute(
            """
            select
                id,
                name,
                username,
                password_hash,
                role,
                active
            from users
            where username=%s
            """,
            (item.username.strip(),)
        ).fetchone()

    if (
        not user
        or not user["active"]
        or not verify_password(
            item.password,
            user["password_hash"]
        )
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos"
        )

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(
            hours=JWT_EXPIRES_HOURS
        )
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "username": user["username"],
            "role": user["role"]
        }
    }


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    )
):

    if not credentials:

        raise HTTPException(
            status_code=401,
            detail="Autenticação obrigatória"
        )

    try:

        return jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

    except jwt.PyJWTError:

        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )


@app.get("/api/me")
def me(user=Depends(current_user)):

    with conn() as c:

        row = c.execute(
            """
            select
                id,
                name,
                username,
                role,
                active
            from users
            where id=%s
            """,
            (user["sub"],)
        ).fetchone()

    if not row or not row["active"]:

        raise HTTPException(
            status_code=401,
            detail="Usuário inativo"
        )

    return {
        **row,
        "id": str(row["id"])
    }


@app.get("/api/employees")
def employees(
    q: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(current_user)
):

    sql = """
        select
            id,
            code,
            name,
            sector,
            cargo,
            status,
            admission_date,
            dismissal_date,
            dismissal_reason
        from employees
    """

    params = []
    clauses = []

    if q:

        clauses.append(
            """
            (
                name ilike %s
                or code ilike %s
                or sector ilike %s
            )
            """
        )

        like = f"%{q}%"

        params += [
            like,
            like,
            like
        ]

    if status:

        clauses.append(
            "status = %s"
        )

        params.append(status)

    if clauses:

        sql += (
            " where "
            + " and ".join(clauses)
        )

    sql += " order by name"

    with conn() as c:

        rows = c.execute(
            sql,
            params
        ).fetchall()

    return rows


@app.get("/api/employees/{employee_id}")
def employee(
    employee_id: str,
    user=Depends(current_user)
):

    with conn() as c:

        employee_row = c.execute(
            """
            select
                id,
                code,
                name,
                sector,
                cargo,
                status,
                admission_date,
                dismissal_date,
                dismissal_reason
            from employees
            where id=%s
            """,
            (employee_id,)
        ).fetchone()

        if not employee_row:

            raise HTTPException(
                404,
                "colaborador não encontrado"
            )

        history = c.execute(
            """
            select
                id,
                event_type,
                details,
                created_at
            from employee_history
            where employee_id=%s
            order by created_at desc
            """,
            (employee_id,)
        ).fetchall()

        vacations = c.execute(
            """
            select
                id,
                accrual_period,
                concession_period,
                start_date,
                end_date,
                status,
                payment_evidence,
                evidence_file
            from vacations
            where employee_id=%s
            order by start_date desc
            """,
            (employee_id,)
        ).fetchall()

        absences = c.execute(
            """
            select
                id,
                absence_type,
                start_date,
                end_date,
                status,
                evidence_file
            from absences
            where employee_id=%s
            order by start_date desc
            """,
            (employee_id,)
        ).fetchall()

        aso = c.execute(
            """
            select
                id,
                exam_type,
                exam_date,
                next_due,
                status,
                evidence_file
            from aso
            where employee_id=%s
            order by exam_date desc
            """,
            (employee_id,)
        ).fetchall()

        documents = c.execute(
            """
            select
                id,
                name,
                category,
                document_number,
                issuing_body,
                issue_date,
                expiration_date,
                responsible,
                substitute,
                status,
                file_path
            from documents
            where employee_id=%s
            order by expiration_date desc
            """,
            (employee_id,)
        ).fetchall()

    return {
        "employee": employee_row,
        "history": history,
        "vacations": vacations,
        "absences": absences,
        "aso": aso,
        "documents": documents
    }


class EmployeeIn(BaseModel):

    code: str
    name: str
    sector: Optional[str] = None
    cargo: Optional[str] = None
    status: str = "Ativo"
    admission_date: Optional[date] = None


@app.post("/api/employees")
def create_employee(
    item: EmployeeIn,
    user=Depends(current_user)
):

    with conn() as c:

        try:

            employee_row = c.execute(
                """
                insert into employees
                (
                    code,
                    name,
                    sector,
                    cargo,
                    status,
                    admission_date
                )
                values (%s,%s,%s,%s,%s,%s)
                returning
                    id,
                    code,
                    name,
                    sector,
                    cargo,
                    status,
                    admission_date
                """,
                (
                    item.code,
                    item.name,
                    item.sector,
                    item.cargo,
                    item.status,
                    item.admission_date
                )
            ).fetchone()

            c.execute(
                """
                insert into employee_history
                (
                    employee_id,
                    event_type,
                    details,
                    created_by
                )
                values (%s,%s,%s,%s)
                """,
                (
                    employee_row["id"],
                    "CADASTRO",
                    json.dumps({
                        "source": "api-hml"
                    }),
                    user["sub"]
                )
            )

            c.execute(
                """
                insert into audit_logs
                (
                    user_id,
                    action,
                    entity,
                    record_id,
                    details
                )
                values (%s,%s,%s,%s,%s)
                """,
                (
                    user["sub"],
                    "CREATE",
                    "employee",
                    str(employee_row["id"]),
                    json.dumps({
                        "code": employee_row["code"]
                    })
                )
            )

            c.commit()

            return employee_row

        except psycopg.errors.UniqueViolation:

            c.rollback()

            raise HTTPException(
                409,
                "código de colaborador já cadastrado"
            )


@app.get("/api/closures")
def closures(
    user=Depends(current_user)
):

    with conn() as c:

        return c.execute(
            """
            select
                id,
                competence,
                status,
                version,
                dp_percent,
                finance_percent,
                closed_at,
                reopen_reason
            from monthly_closures
            order by competence desc
            """
        ).fetchall()


@app.get("/api/audit")
def audit(
    limit: int = 200,
    user=Depends(current_user)
):

    limit = max(
        1,
        min(limit, 1000)
    )

    with conn() as c:

        return c.execute(
            """
            select
                id,
                user_id,
                action,
                entity,
                record_id,
                details,
                created_at
            from audit_logs
            order by id desc
            limit %s
            """,
            (limit,)
        ).fetchall()
