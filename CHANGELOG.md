# Changelog

## [2026-06-16]



## [2026-06-15 - 2026-06-16]

### Project Restructure
- Moved entire Django project (Django Ninja apps, `manage.py`, `Dockerfile`, `entrypoint.sh`) into a top-level `app/` folder, with `pyproject.toml` and `uv.lock` remaining at repo root.
- Updated `INSTALLED_APPS` to use dotted paths reflecting the new structure (e.g. `app.access`, `app.users`, `app.organization`).
- Fixed each app's `apps.py` (`AccessConfig`, `UsersConfig`, `OrganizationConfig`) `name` attribute to match the new `app.<name>` dotted path — this was the root cause of `ModuleNotFoundError: No module named 'access'` during Django app loading and mypy's Django plugin initialization.

### Mypy / Type Checking
- Added `mypy_path = "."` to `[tool.mypy]` in `pyproject.toml` so mypy can resolve the `app` package from the project root regardless of pre-commit's working directory.
- Fixed `app/access/auth.py`:
  - Removed an unused `# type: ignore` comment on the `ninja_jwt` import.
  - Added `# type: ignore[misc]` on `class JWTAuth(BaseJWTAuth)` since `BaseJWTAuth` is untyped (`Any`).
  - Fixed `authenticate` method signature — argument order was swapped (`token, request` instead of `request, token`) and `token` was missing a type annotation.
  - Replaced invalid `User | None` return annotation (using the runtime `get_user_model()` value as a type) with `AbstractBaseUser | None`.
  - Added missing `-> None` return annotation on `TokenManager.mark_use`.
- Fixed `app/access/services.py`:
  - `create_email_verify_token_service` no longer references a nonexistent `data.created_at` field; now relies on `TokenManager.generate_token`'s internal `expires_in` default instead of computing expiry from client input.
  - Removed `expires_at` from `VerificationTokenCreateSchema.Meta.fields` since expiry is computed server-side, not client-supplied.
  - Fixed `verify_email_service`: corrected broken `TokenManager.verify_token(**data.model_dump().values())` call (invalid unpacking of `dict_values`) to pass `token=` and `token_type=` explicitly; added `isinstance` check to properly narrow the `bool | VerificationTokens` return type for mypy.
  - Fixed `get_verification_token_service`: corrected `filter_options` dict typing (`dict[str, int | str]`), removed invalid `token.isinstance(...)` syntax, and changed to return schema instances instead of `.model_dump()` dicts to match the declared return type.
  - Fixed `login_service` and ensured both it and `refresh_token_service` return `LoginResponseSchema` instances (not `.model_dump()` dicts), matching their declared return types.
- Fixed `app/access/views.py`:
  - `get_verification_token` endpoint changed from accepting a full `VerificationTokenSchema` body on a GET request to proper optional query parameters (`token_id`, `token_type`, `user_id`).
  - `create_email_verification_token` now correctly types its payload as `VerificationTokenCreateSchema` instead of `VerificationTokenSchema`.
  - `verify_email_token` now correctly types its payload as `VerifyEmailSchema` instead of `VerificationTokenSchema`.
- Fixed `app/config/urls.py`: removed the `csrf=False` keyword argument from `NinjaAPI(...)` instantiation — no longer a valid constructor parameter in the installed django-ninja version.

### Models
- `Terminals` model: fixed `max_length="50"` (string) to `max_length=50` (int) on `longitude`/`latitude`; fixed `organization` FK from invalid `SET_NULL` without `null=True` to `CASCADE`; fixed `created_at` (was `auto_now`, should be `auto_now_add`) and `updated_at` (was `DateField` with no auto behavior, now `DateTimeField(auto_now=True)`).
- `Gates` model: fixed invalid `TextChoices` syntax (`"ENTRY" = "entry"` is not valid Python) to proper `ENTRY = "entry", "Entry"` form; added missing `choices=` kwarg on `gate_type` field; fixed `max_length` string-vs-int issue.
- Decided `Gate` stays inside the `terminals` app/module (tightly coupled, no independent lifecycle) rather than its own app.
- Confirmed relationship design: `Organization → Terminals` is one-to-many (FK on `Terminals`, `on_delete=CASCADE`, since a terminal can't exist without an org); `Terminal → Gates` is one-to-many (FK on `Gates`); both directions allow zero-or-many on the "many" side with no schema change needed for the "zero" case.
- Decided terminal closure/removal should be modeled via a `status` field (`active` / `closed` / `decommissioned`) on `Terminals` rather than deletion, to preserve historical data (RFID events, routes) tied to a terminal.
- Reviewed `RfidEvent` / `RfidAlert` relationship design for the upcoming RFID module: `RfidAlert` will have an optional FK to `RfidEvent` (`SET_NULL`, nullable — covers alerts not tied to a single event, e.g. timeout/absence alerts) plus a direct FK to `Terminal` for query convenience and to cover the null-event case.
- Reviewed `users/models.py`:
  - Identified `User.organization` FK using `CASCADE` without `null=True` as too aggressive (deletes users if their org is deleted); recommended `PROTECT` instead.
  - Identified `OfficeProfile`/`DriverProfile` subclassing a concrete `UserProfile` model as unintended Django multi-table inheritance (extra joins, extra DB table); recommended converting `UserProfile` to an abstract base class (`class Meta: abstract = True`) so each subclass gets its own complete table.
  - Recommended adding explicit `related_name` to the `OneToOneField` on `UserProfile` for clearer reverse access (`user.office_profile` / `user.driver_profile`).

### App Architecture Decisions
- Decided fleet-related entities (trucks, terminals, products, gates) will be separate Django apps rather than nested sub-packages within one `fleet` app, to stay consistent with the existing `access`/`users`/`organization` pattern and avoid non-standard model/migration discovery overrides.
- Decided the upcoming RFID module (MQTT-based) will be its own app (`rfid`), referencing `trucks` and `terminals` via cross-app FKs (string references, e.g. `ForeignKey("terminals.Terminal", ...)`), with the MQTT listener implemented as a custom Django management command so it can run as its own process/container alongside the main app.

### Build / Tooling
- Fixed Makefile `app` target: was missing `.PHONY` declaration (make treated `app` as a stale file target equal to the `app/` directory) and was missing a destination argument for `startapp`, causing new apps to be scaffolded at repo root instead of inside `app/`. Now: `$(MANAGE) startapp $(name) app/$(name)`, invoked via `make app name=<appname>`.
- Fixed "missing separator" Makefile error caused by spaces instead of tabs indenting recipe lines.

### Docker
- Fixed Dockerfile `COPY` paths after the project restructure: `pyproject.toml`/`uv.lock` `COPY` lines no longer use invalid `../` parent-directory references; build context changed to repo root with `dockerfile: app/Dockerfile` in `docker-compose.yml`, and `COPY app/ .` / `COPY app/entrypoint.sh /entrypoint.sh` added to correctly pull Django project files from the `app/` subdirectory into the image's `/app`.
- Fixed `docker-compose.yml` bind mount: `- .:/app` was mounting the entire repo root (which now contains `app/`, `pyproject.toml`, etc., not `manage.py` directly) over `/app`, hiding everything the image had built there (including the venv) and causing `manage.py: No such file or directory`. Changed to `- ./app:/app`.
- Moved the Python virtual environment from `/app/.venv` to `/opt/venv` in the Dockerfile (both build and runtime stages, plus `PATH`), so the `./app:/app` bind mount can no longer shadow/hide the venv at container runtime. This was the root cause of `ModuleNotFoundError: No module named 'django'` after the bind-mount path was corrected.
- Removed a duplicate `EXPOSE 8001` line.
- Simplified `entrypoint.sh` to rely on `PATH` (set in the Dockerfile) rather than hardcoding `/app/.venv/bin/python` paths, which had gone stale after the venv relocation.

### Notes / Open Items
- `Digital Executive` role offer still pending — no code-related action needed, just tracked as context.
- Still need to apply the `User.organization` `on_delete=PROTECT` change and the `UserProfile` abstract-base-class refactor to actual model files (discussed, not yet committed as of this session).
- RFID module (`rfid` app, MQTT listener, `RfidEvent`/`RfidAlert` models) is designed but not yet implemented.
