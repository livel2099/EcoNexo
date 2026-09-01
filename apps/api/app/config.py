"""Configuración tipada de EcoNexo para desarrollo y producción."""
from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    release_version: str = "1.0.0-rc.6.2"

    database_url: str = ""
    # Opcional: una conexión directa separada para DDL/migraciones. Si no se
    # define, las migraciones usan DATABASE_URL igual que la aplicación.
    migrations_database_url: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "econexo"
    postgres_user: str = "econexo"
    postgres_password: str = "econexo_dev_pw"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_command_timeout_seconds: float = 30.0
    # Supabase instala postgis, uuid-ossp y pgcrypto en el esquema `extensions`,
    # no en `public`. Sin este search_path, `uuid_generate_v4()` y las funciones
    # ST_* no resuelven y la migracion 01 falla en el primer DEFAULT. Postgres
    # ignora en silencio los esquemas del search_path que no existen, asi que el
    # valor por defecto tambien sirve para el Postgres local del compose.
    db_search_path: str = "public,extensions"
    # asyncpg cachea prepared statements. El Session pooler de Supabase (5432)
    # lo soporta; el Transaction pooler (6543) no, y responde
    # "prepared statement already exists". Poner 0 desactiva el cache.
    db_statement_cache_size: int = 100

    jwt_secret: str = "change_me_dev_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    internal_service_token: str = "change_me_internal_dev_secret"
    forwarded_allow_ips: str = "127.0.0.1"

    google_client_id: str = ""
    google_client_ids: str = ""
    login_attempt_limit: int = 10
    login_attempt_window_seconds: int = 15 * 60

    platform_admin_emails: str = ""
    platform_admin_bootstrap_enabled: bool = False
    platform_admin_initial_password: str = ""
    platform_admin_force_password_change: bool = True
    platform_admin_reset_initial_password: bool = False
    platform_admin_name: str = "Administrador General EcoNexo"
    platform_admin_organization: str = "EcoNexo Plataforma"
    sales_email: str = ""

    mqtt_enabled: bool = True
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    s3_enabled: bool = True
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "econexo-reports"
    s3_access_key: str = "econexo"
    s3_secret_key: str = "econexo_dev_pw"
    s3_server_side_encryption: str = ""
    max_report_photo_bytes: int = 8 * 1024 * 1024

    anomaly_enabled: bool = True
    anomaly_service_url: str = "http://localhost:8100"

    public_app_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    # Origen público del frontend cuando se despliega como Static Site en
    # Render. Se mantiene separado de PUBLIC_APP_URL para que una corrección
    # del dominio web no deje al API sin su origen CORS durante un redeploy.
    econexo_web_origin: str = ""

    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    # El archivo devuelve cientos de dias por consulta: necesita mas aire que
    # el pronostico, sobre todo desde una IP de salida compartida.
    agro_http_timeout_seconds: float = 45.0
    agro_http_retries: int = 3
    nasa_firms_key: str = ""
    firms_inline_enabled: bool = True
    firms_source: str = "VIIRS_SNPP_NRT"
    pipeline_max_devices_per_run: int = 100
    pipeline_http_timeout_seconds: float = 20.0
    pipeline_scheduler_enabled: bool = True

    copernicus_enabled_by_default: bool = True
    copernicus_mode: str = "process_api"
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    copernicus_token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    copernicus_process_url: str = "https://sh.dataspace.copernicus.eu/process/v1"
    copernicus_instance_id: str = ""
    copernicus_wms_url: str = ""
    copernicus_http_timeout_seconds: float = 45.0
    copernicus_time_range_days: int = 90
    copernicus_max_cloud_coverage: int = 80
    copernicus_max_dimension: int = 1024
    copernicus_cache_seconds: int = 600

    @property
    def dsn(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def migration_dsn(self) -> str:
        return self.migrations_database_url.strip() or self.dsn

    @property
    def db_connect_kwargs(self) -> dict[str, object]:
        """Parametros comunes a todas las conexiones asyncpg del proyecto.

        Centralizado para que el pool del API, las migraciones y el seeder
        hablen con la misma base de la misma forma. Antes cada uno abria la
        conexion por su cuenta y solo el pool tenia timeout configurado.
        """
        return {
            "server_settings": {"search_path": self.db_search_path.strip() or "public"},
            "statement_cache_size": max(0, self.db_statement_cache_size),
        }

    @staticmethod
    def _dsn_query(dsn: str) -> str:
        """Query string del DSN sin pasar por urlparse.

        urlparse levanta ValueError si el netloc trae corchetes: los interpreta
        como un host IPv6 y valida el contenido como direccion. Una contraseña
        con `[` o `]` sin codificar rompia el arranque con un traceback que
        hablaba de IPv6 y no decia nada de la contraseña. Segun la RFC 3986 el
        primer `?` abre la query, asi que alcanza con cortar ahi.
        """
        _, separador, query = dsn.partition("?")
        return query if separador else ""

    @classmethod
    def _dsn_has_tls(cls, dsn: str) -> bool:
        modes = [
            value.split("=", 1)[1].strip().lower()
            for value in cls._dsn_query(dsn).split("&")
            if value.strip().lower().startswith("sslmode=")
        ]
        return bool(modes) and modes[-1] not in {"disable", "allow", "prefer"}

    @staticmethod
    def describe_dsn(dsn: str) -> str:
        """`usuario@host:puerto/base` sin la contraseña, para log.

        Un `getaddrinfo: Name or service not known` no dice que host intento
        resolver, asi que no se puede distinguir entre una URL mal cargada y un
        problema de red sin adivinar. Se parsea a mano, nunca con urlparse: si
        la contraseña trae caracteres reservados esto tiene que seguir
        funcionando, que es justo cuando mas se lo necesita.
        """
        if not dsn.strip():
            return "(vacia)"
        resto = dsn.split("://", 1)[-1]
        resto = resto.split("?", 1)[0]
        netloc, _, ruta = resto.partition("/")
        # rsplit: la contraseña puede tener un `@` sin codificar, el separador
        # real es el ultimo.
        userinfo, _, hostport = netloc.rpartition("@")
        usuario = userinfo.split(":", 1)[0] if userinfo else "(sin usuario)"
        return f"{usuario}@{hostport or '(sin host)'}/{ruta or '(sin base)'}"

    @staticmethod
    def _dsn_is_parseable(dsn: str) -> bool:
        """Anticipa el mismo ValueError que asyncpg lanzaria al conectar.

        asyncpg parsea el DSN con urlparse, asi que un caracter reservado sin
        codificar en la contraseña (`[`, `]`, `@`, `/`, `?`, `#`) no es solo un
        problema de esta validacion: la conexion tampoco se va a poder abrir.
        """
        try:
            urlparse(dsn)
        except ValueError:
            return False
        return True

    @property
    def cors_list(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        for origin in (self.public_app_url, self.econexo_web_origin):
            normalized = origin.strip().rstrip("/")
            if normalized and normalized not in origins:
                origins.append(normalized)
        expanded = list(origins)
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.hostname == "localhost":
                loopback = origin.replace("localhost", "127.0.0.1", 1)
                if loopback not in expanded:
                    expanded.append(loopback)
            elif parsed.hostname == "127.0.0.1":
                localhost = origin.replace("127.0.0.1", "localhost", 1)
                if localhost not in expanded:
                    expanded.append(localhost)
        return expanded

    @property
    def platform_admin_list(self) -> list[str]:
        return sorted({email.strip().lower() for email in self.platform_admin_emails.split(",") if email.strip()})

    @property
    def google_audiences(self) -> list[str]:
        values = [self.google_client_id, *self.google_client_ids.split(",")]
        return sorted({value.strip() for value in values if value.strip()})

    @property
    def google_client_id_list(self) -> list[str]:
        return self.google_audiences

    @property
    def copernicus_mode_normalized(self) -> str:
        mode = self.copernicus_mode.strip().lower()
        return mode if mode in {"process_api", "wms"} else "process_api"

    @property
    def copernicus_process_configured(self) -> bool:
        return bool(self.copernicus_client_id.strip() and self.copernicus_client_secret.strip())

    @staticmethod
    def _placeholder(value: str) -> bool:
        normalized = value.strip().lower()
        return not normalized or any(token in normalized for token in ("change_me", "reemplazar", "contrasena", "usuario", "example-secret"))

    def insecure_production_values(self) -> list[str]:
        if self.environment.strip().lower() not in {"production", "prod"}:
            return []
        findings: list[str] = []
        if len(self.jwt_secret) < 32 or self._placeholder(self.jwt_secret):
            findings.append("JWT_SECRET")
        if len(self.internal_service_token) < 32 or self._placeholder(self.internal_service_token):
            findings.append("INTERNAL_SERVICE_TOKEN")
        if not self.public_app_url.startswith("https://"):
            findings.append("PUBLIC_APP_URL")
        if "*" in self.cors_list or any(not origin.startswith("https://") for origin in self.cors_list):
            findings.append("CORS_ORIGINS")
        if os.getenv("RENDER_SERVICE_ID") and self._placeholder(self.database_url):
            findings.append("DATABASE_URL")
        # La base dejo de ser un servicio interno de Render: ahora el trafico
        # sale a internet hacia Supabase. Sin sslmode explicito, libpq/asyncpg
        # aceptan texto plano si el servidor lo ofrece.
        elif self.database_url.strip():
            if not self._dsn_is_parseable(self.database_url):
                findings.append("DATABASE_URL_ENCODING")
            if not self._dsn_has_tls(self.database_url):
                findings.append("DATABASE_URL_SSLMODE")
        if self.migrations_database_url.strip():
            if not self._dsn_is_parseable(self.migrations_database_url):
                findings.append("MIGRATIONS_DATABASE_URL_ENCODING")
            if not self._dsn_has_tls(self.migrations_database_url):
                findings.append("MIGRATIONS_DATABASE_URL_SSLMODE")
        if self.platform_admin_bootstrap_enabled and (
            not self.platform_admin_list or len(self.platform_admin_initial_password) < 12
        ):
            findings.append("PLATFORM_ADMIN_INITIAL_PASSWORD")
        if self.s3_enabled:
            if not self.s3_public_endpoint.startswith("https://"):
                findings.append("S3_PUBLIC_ENDPOINT")
            if not self.s3_server_side_encryption.strip():
                findings.append("S3_SERVER_SIDE_ENCRYPTION")
            if self._placeholder(self.s3_secret_key):
                findings.append("S3_SECRET_KEY")
        if bool(self.copernicus_client_id.strip()) != bool(self.copernicus_client_secret.strip()):
            findings.append("COPERNICUS_CLIENT_ID/COPERNICUS_CLIENT_SECRET")
        return findings


@lru_cache
def get_settings() -> Settings:
    return Settings()