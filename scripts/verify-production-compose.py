import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as scratch:
    target = Path(scratch)
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        shutil.copyfile(root / name, target / name)
    for name in (".env", ".env.production"):
        (target / name).write_text("")
    environment = {**os.environ, "SECRET_KEY": "synthetic-production-validation-key-only", "DATABASE_URL": "postgresql+asyncpg://prod:synthetic@postgres:5432/platform", "REDIS_URL": "redis://:synthetic@redis:6379/0", "REDIS_PASSWORD": "synthetic", "POSTGRES_USER": "prod", "POSTGRES_PASSWORD": "synthetic", "CORS_ORIGINS": '["https://example.invalid"]', "DOMAIN": "example.invalid", "NEXT_PUBLIC_API_URL": "", "NEXT_PUBLIC_WS_URL": ""}
    result = subprocess.run(["docker", "compose", "--env-file", str(target / ".env.production"), "-f", str(target / "docker-compose.yml"), "-f", str(target / "docker-compose.prod.yml"), "config", "--format", "json"], env=environment, capture_output=True, text=True, timeout=30, check=True)
    services = json.loads(result.stdout)["services"]
    for name in ("postgres", "redis", "backend", "frontend"):
        assert not services[name].get("ports"), f"Production {name} exposes an inherited port"
    for name in ("backend", "frontend"):
        assert not services[name].get("volumes"), f"Production {name} inherits development mounts"
    backend = services["backend"]
    assert backend["environment"]["APP_ENV"] == "production"
    for key in ("SECRET_KEY", "DATABASE_URL", "REDIS_URL", "CORS_ORIGINS"):
        assert backend["environment"][key] == environment[key], f"Development {key} overrides production"
    assert backend["build"]["target"] == "production"
    assert services["frontend"]["build"]["target"] == "runner"
    assert services["frontend"]["build"]["args"]["NEXT_PUBLIC_API_URL"] == ""
    assert services["redis"]["environment"]["REDISCLI_AUTH"] == "synthetic"
    assert services["proxy"]["environment"]["DOMAIN"] == "example.invalid"
    assert {port["published"] for port in services["proxy"]["ports"]} == {"80", "443"}
print("Production Compose merge verified: private services, no development mounts, explicit production identity, authenticated Redis, build-time browser origins, proxy domain")
