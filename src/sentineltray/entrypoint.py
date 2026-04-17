from __future__ import annotations

import atexit
import ctypes
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .config import AppConfig, get_project_root, get_user_data_dir, get_user_log_dir, load_config
from .console_app import run_console_config_error
from .gui_app import prompt_smtp_password_gui, run_gui
from .email_sender import EmailAuthError, validate_smtp_credentials
from .logging_setup import setup_logging
from .dpapi_utils import save_secret
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)
_mutex_handle = None

_CONFIG_TEMPLATE = r"""# SentinelTray — Configuração.
# Copie este arquivo para config.local.yaml e preencha com seus valores.
# NÃO armazene smtp_password aqui — deixe em branco e informe na primeira
# inicialização; a senha será salva criptografada em smtp_password_<n>.dpapi.

# ─────────────────────────────────────────────────────────────────────────────
# MONITORS — lista de janelas a serem monitoradas
# Cada item representa uma janela de aplicação e as regras de alerta por e-mail.
# ─────────────────────────────────────────────────────────────────────────────
monitors:
- # Expressão regular (regex) comparada contra o título da janela do processo.
  # Use '\\.' para escapar pontos literais no nome do executável.
  # Exemplo: 'MinhaApp\\.exe' corresponde a "MinhaApp.exe".
  window_title_regex: 'Sino\.Siscam'

  # Expressão regular (regex) comparada contra o texto visível dentro da janela.
  # Quando o texto da janela casar com este padrão, um alerta será disparado.
  # Exemplo: 'ERRO CRÍTICO|FALHA' dispara ao detectar qualquer dessas frases.
  phrase_regex: 'NÃO RECEBID'

  # Configurações de envio de e-mail para este monitor específico.
  email:
    # Endereço do servidor SMTP utilizado para enviar os e-mails de alerta.
    # Exemplos: 'smtp.gmail.com', 'smtp.office365.com', 'mail.empresa.com.br'
    smtp_host: 'smtp.gmail.com'

    # Porta do servidor SMTP.
    # Valores comuns: 587 (STARTTLS/TLS), 465 (SSL), 25 (sem criptografia).
    smtp_port: 587

    # Nome de usuário (geralmente o endereço de e-mail) para autenticação no SMTP.
    smtp_username: 'sentineltray@gmail.com'

    # Senha SMTP. Deixe SEMPRE vazio aqui.
    # O SentinelTray solicitará a senha interativamente na primeira execução
    # e a armazenará de forma segura via DPAPI (Windows Data Protection API)
    # no arquivo smtp_password_<n>.dpapi, na pasta config/.
    smtp_password: ''

    # Endereço de e-mail que aparecerá como remetente nas mensagens enviadas.
    # Normalmente igual ao smtp_username, mas pode ser um alias configurado
    # no provedor de e-mail.
    from_address: 'sentineltray@gmail.com'

    # Lista de endereços de e-mail que receberão os alertas.
    # Pode conter múltiplos destinatários: ['dest1@exemplo.com', 'dest2@exemplo.com']
    to_addresses: ['chrmsantos@proton.me']

    # Habilita criptografia TLS/STARTTLS na conexão SMTP.
    # Recomendado: true. Desative apenas em servidores internos sem suporte a TLS.
    use_tls: true

    # Tempo máximo (em segundos) aguardado para estabelecer conexão e enviar o e-mail.
    # Aumentar esse valor pode ajudar em redes lentas ou servidores com alta latência.
    timeout_seconds: 10

    # Assunto padrão dos e-mails de alerta enviados por este monitor.
    subject: SentinelTray

    # Número de tentativas de reenvio em caso de falha no envio do e-mail.
    # Após todas as tentativas falharem, a mensagem vai para a fila persistente.
    retry_attempts: 2

    # Tempo de espera (em segundos) entre tentativas consecutivas de reenvio.
    # Segue estratégia de backoff linear: cada tentativa espera esse valor multiplicado
    # pelo número da tentativa.
    retry_backoff_seconds: 3

# ─────────────────────────────────────────────────────────────────────────────
# POLLING & TIMING — controle de frequência de verificação
# ─────────────────────────────────────────────────────────────────────────────

# Intervalo (em segundos) entre cada varredura nas janelas monitoradas.
# Valores menores tornam a detecção mais rápida, mas aumentam o uso de CPU.
# Recomendado: entre 30 e 120 segundos para uso geral.
poll_interval_seconds: 30

# Intervalo (em segundos) entre verificações de "saúde" (healthcheck) do sistema.
# O healthcheck registra um log periódico confirmando que o SentinelTray está ativo.
# Valor padrão: 1800 (30 minutos).
healthcheck_interval_seconds: 1800

# Tempo base (em segundos) para o backoff exponencial em caso de erros gerais.
# Na primeira falha, o sistema aguarda esse valor antes de tentar novamente.
# A cada falha consecutiva, o tempo dobra até atingir error_backoff_max_seconds.
error_backoff_base_seconds: 5

# Tempo máximo (em segundos) que o backoff exponencial pode atingir.
# Limita o crescimento do intervalo de espera após falhas repetidas.
error_backoff_max_seconds: 300

# Janela de supressão de alertas duplicados (em segundos) por monitor.
# Após um alerta ser enviado, novos alertas do mesmo monitor são ignorados
# durante esse período, evitando spam de e-mails para o mesmo evento.
# Exemplo: 600 = 10 minutos de silêncio após cada alerta.
debounce_seconds: 1800

# Número máximo de entradas mantidas no histórico de correspondências por monitor.
# O histórico é usado para detectar alertas repetidos e calcular deltas.
# Entradas mais antigas são descartadas quando o limite é atingido.
max_history: 50

# ─────────────────────────────────────────────────────────────────────────────
# ARQUIVOS & LOGS — caminhos e configurações de registro
# ─────────────────────────────────────────────────────────────────────────────

# Caminho do arquivo de estado persistente do SentinelTray.
# Armazena o histórico de alertas e o estado dos monitores entre reinicializações.
# Caminho relativo à pasta de dados do aplicativo (config/).
state_file: state.json

# Caminho do arquivo de log principal (formato texto rotacionado).
# Registra eventos, erros e informações de operação do SentinelTray.
log_file: logs/sentineltray.log

# Nível mínimo de severidade para gravar no arquivo de log.
# Opções (do mais detalhado ao menos): DEBUG, INFO, WARNING, ERROR, CRITICAL.
# Recomendado: INFO para produção, DEBUG para diagnóstico de problemas.
log_level: INFO

# Nível mínimo de severidade para exibir mensagens no console (stdout/stderr).
# Independente de log_level; útil para ver avisos críticos sem poluir o log.
log_console_level: WARNING

# Habilita ou desabilita a saída de log no console.
# Desative (false) para suprimir toda saída no console em execução silenciosa.
log_console_enabled: true

# Tamanho máximo (em bytes) de cada arquivo de log antes de ser rotacionado.
# 5000000 = ~4,8 MB. Ao atingir o limite, o arquivo atual é renomeado
# e um novo arquivo de log é criado.
log_max_bytes: 5000000

# Número de arquivos de log rotacionados a manter além do arquivo atual.
# Exemplo: 3 mantém sentineltray.log, sentineltray.log.1, .log.2 e .log.3.
# Arquivos mais antigos são automaticamente removidos.
log_backup_count: 3

# Quantidade de arquivos de log de execução (run logs) a preservar.
# Logs de execução são criados a cada inicialização do SentinelTray.
# Execuções mais antigas além desse limite são excluídas automaticamente.
log_run_files_keep: 3

# Caminho do arquivo de telemetria (formato JSON Lines).
# Registra eventos estruturados para análise de uso e diagnóstico.
# Não contém dados sensíveis; pode ser compartilhado para suporte.
telemetry_file: logs/telemetry.json

# ─────────────────────────────────────────────────────────────────────────────
# COMPORTAMENTO — controle de como o SentinelTray reage aos eventos
# ─────────────────────────────────────────────────────────────────────────────

# Permite que o SentinelTray restaure janelas minimizadas para ler seu conteúdo.
# Algumas janelas só expõem seu texto quando estão visíveis/restauradas.
# Desative (false) se não quiser que o aplicativo altere o estado das janelas.
allow_window_restore: true

# Modo somente log: quando true, alertas são registrados no log mas NÃO são
# enviados por e-mail. Útil para testar configurações sem disparar e-mails reais.
log_only_mode: false

# Permite reenviar alertas para correspondências que já foram detectadas antes.
# Quando true, o mesmo alerta pode ser enviado novamente após debounce_seconds.
# Quando false, cada correspondência única é alertada apenas uma vez.
send_repeated_matches: true

# Intervalo mínimo (em segundos) entre alertas repetidos do mesmo monitor.
# 0 = sem restrição adicional além de debounce_seconds.
# Use este valor para impor um silêncio mínimo entre alertas repetidos.
min_repeat_seconds: 0

# Tempo de espera (em segundos) antes de reenviar uma notificação de erro.
# Evita spam de e-mails de erro em caso de falhas contínuas (ex.: SMTP fora do ar).
# Exemplo: 300 = no máximo um e-mail de erro a cada 5 minutos.
error_notification_cooldown_seconds: 300

# ─────────────────────────────────────────────────────────────────────────────
# CIRCUIT BREAKER DE JANELA — proteção contra erros repetidos ao ler janelas
# ─────────────────────────────────────────────────────────────────────────────

# Tempo base (em segundos) de backoff ao falhar ao acessar uma janela monitorada.
# Segue o mesmo padrão exponencial de error_backoff_base_seconds.
window_error_backoff_base_seconds: 5

# Tempo máximo (em segundos) de backoff para erros de acesso a janelas.
# Após esse limite, o backoff para de crescer para aquela janela.
window_error_backoff_max_seconds: 120

# Número de falhas consecutivas de acesso a uma janela que ativa o circuit breaker.
# Quando atingido, a janela é temporariamente ignorada para evitar loops de erro.
window_error_circuit_threshold: 3

# Tempo (em segundos) que o circuit breaker mantém a janela desativada após
# ser acionado. Após esse período, o SentinelTray tenta acessar a janela novamente.
window_error_circuit_seconds: 300

# ─────────────────────────────────────────────────────────────────────────────
# FILA DE E-MAILS — persistência de e-mails com falha no envio
# ─────────────────────────────────────────────────────────────────────────────

# Caminho do arquivo de fila persistente de e-mails.
# E-mails que falham em todas as tentativas imediatas são enfileirados aqui
# e reenviados automaticamente nas próximas execuções.
email_queue_file: logs/email_queue.json

# Número máximo de e-mails que podem estar na fila simultaneamente.
# Ao atingir o limite, novos e-mails com falha são descartados (com aviso no log).
email_queue_max_items: 500

# Idade máxima (em segundos) de um e-mail na fila antes de ser descartado.
# 86400 = 24 horas. E-mails mais antigos que isso são removidos da fila
# mesmo se ainda não tiverem sido enviados com sucesso.
email_queue_max_age_seconds: 86400

# Número máximo de tentativas de envio para cada e-mail na fila.
# Após esse número de tentativas fracassadas, o e-mail é descartado da fila.
email_queue_max_attempts: 10

# Tempo base (em segundos) de backoff entre tentativas de reenvio da fila.
# A espera cresce exponencialmente: 30s, 60s, 120s... até email_backoff_max.
email_queue_retry_base_seconds: 30

# ─────────────────────────────────────────────────────────────────────────────
# PAUSA POR ATIVIDADE — evita alertas enquanto o usuário está no computador
# ─────────────────────────────────────────────────────────────────────────────

# Quando true, suspende o envio de alertas enquanto o usuário está ativo no PC.
# Útil para evitar interrupções quando o operador está monitorando manualmente.
# A detecção de atividade usa o tempo de ociosidade do sistema operacional.
pause_on_user_active: true

# Tempo de ociosidade (em segundos) necessário para considerar o usuário inativo.
# O SentinelTray só retoma o envio de alertas após o usuário ficar inativo
# por pelo menos esse período.
# Exemplo: 120 = 2 minutos sem atividade de teclado/mouse para retomar alertas.
pause_idle_threshold_seconds: 120
"""


def _pid_file_path() -> Path:
    base = get_user_data_dir()
    return base / "sentineltray.pid"


def _show_already_running_notice() -> None:
    message = (
        "SentinelTray já está em execução.\n\n"
        "Use a janela do console para acessar Config e Status."
    )
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "SentinelTray",
            0x00000040,
        )
    except Exception:
        sys.stderr.write(f"{message}\n")


def _ensure_single_instance_mutex() -> bool:
    global _mutex_handle
    try:
        kernel32 = ctypes.windll.kernel32
    except Exception:
        return True
    # Incorporate the project root into the mutex name so that different
    # installations (e.g. separate test sandboxes) don't interfere with
    # each other while still preventing two instances from the same root.
    root_hash = hashlib.sha256(str(get_project_root()).encode()).hexdigest()[:8]
    for scope in ("Global", "Local"):
        name = f"{scope}\\SentinelTrayMutex_{root_hash}"
        try:
            mutex = kernel32.CreateMutexW(None, False, name)
            _mutex_handle = mutex
            if kernel32.GetLastError() == 183:
                return False
            if mutex:
                LOGGER.info(
                    "Single-instance mutex acquired: %s",
                    name,
                    extra={"category": "startup"},
                )
                return True
        except Exception as exc:
            LOGGER.warning(
                "Failed to create mutex %s: %s",
                name,
                exc,
                extra={"category": "startup"},
            )
            continue
    return True


def _ensure_single_instance() -> None:
    if not _ensure_single_instance_mutex():
        terminated = _terminate_existing_instance()
        if terminated:
            for _ in range(6):
                time.sleep(0.5)
                if _ensure_single_instance_mutex():
                    break
            else:
                LOGGER.error(
                    "Failed to acquire single-instance mutex after termination",
                    extra={"category": "startup"},
                )
                _show_already_running_notice()
                raise SystemExit(0)
        else:
            _show_already_running_notice()
            raise SystemExit(0)
    pid_path = _pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    if pid_path.exists():
        try:
            pid_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup() -> None:
        try:
            if (
                pid_path.exists()
                and pid_path.read_text(encoding="utf-8").strip() == str(os.getpid())
            ):
                pid_path.unlink()
        except Exception:
            return

    atexit.register(_cleanup)


def _get_process_name(pid: int) -> str | None:
    """Return the executable name of the given PID, or None if it cannot be determined."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line.startswith('"'):
                    return line.split('"')[1].lower()
    except Exception:
        pass
    return None


def _terminate_existing_instance() -> bool:
    pid_path = _pid_file_path()
    if not pid_path.exists():
        LOGGER.warning(
            "Single-instance mutex exists but PID file is missing",
            extra={"category": "startup"},
        )
        return False
    try:
        prior_pid = pid_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        LOGGER.warning(
            "Failed to read PID file for termination: %s",
            exc,
            extra={"category": "startup"},
        )
        return False
    if not prior_pid:
        LOGGER.warning(
            "PID file was empty; cannot terminate prior instance",
            extra={"category": "startup"},
        )
        return False
    try:
        pid_value = int(prior_pid)
        if pid_value < 2:
            raise ValueError(f"PID {pid_value!r} is implausibly low")
    except ValueError as exc:
        LOGGER.warning(
            "PID file contains invalid value %r: %s",
            prior_pid,
            exc,
            extra={"category": "startup"},
        )
        return False
    process_name = _get_process_name(pid_value)
    if process_name is not None and "sentineltray" not in process_name and "python" not in process_name:
        LOGGER.warning(
            "PID %s belongs to '%s', not SentinelTray; skipping termination to avoid killing an unrelated process",
            pid_value,
            process_name,
            extra={"category": "startup"},
        )
        return False
    LOGGER.info(
        "Existing instance detected; terminating PID %s",
        pid_value,
        extra={"category": "startup"},
    )
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid_value), "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        LOGGER.error(
            "Failed to terminate prior instance PID %s: %s",
            prior_pid,
            exc,
            extra={"category": "startup"},
        )
        return False
    if result.returncode != 0:
        LOGGER.error(
            "taskkill failed for PID %s: %s",
            prior_pid,
            result.stderr.strip(),
            extra={"category": "startup"},
        )
        return False
    try:
        pid_path.unlink()
    except Exception:
        pass
    return True


def _ensure_local_override(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        meipass = getattr(sys, "_MEIPASS", None)
        candidates = []
        if meipass:
            candidates.append(Path(meipass) / "config" / "config.local.yaml.example")
        candidates.append(get_project_root() / "config" / "config.local.yaml.example")
        template_content: str | None = None
        for example_path in candidates:
            try:
                template_content = example_path.read_text(encoding="utf-8")
                break
            except Exception:
                continue
        if template_content is None:
            template_content = _CONFIG_TEMPLATE
        path.write_text(template_content, encoding="utf-8")
        LOGGER.info(
            "Config template created at %s",
            path,
            extra={"category": "config"},
        )
        try:
            subprocess.Popen(["notepad.exe", str(path)])
        except Exception:
            pass
        raise SystemExit(
            "Configuration template created.\n"
            f"File: {path}\n"
            "Fill in your values (SMTP host, credentials, window title, etc.), "
            "save, and restart SentinelTray."
        )

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise SystemExit(
            "Local configuration is empty.\n"
            f"File: {path}\n"
            "Fill the required fields, save, and run again."
        )


def _handle_config_error(path: Path, exc: Exception) -> str:
    reason = str(exc)
    message = (
        "Configuration error.\n\n"
        f"Config file: {path}\n"
        f"Details: {reason}\n\n"
        "Review the YAML formatting and required fields.\n"
        "After fixing, reopen SentinelTray.\n\n"
        "Quick actions:\n"
        "- Use the console menu: Config (opens an editable temporary file).\n"
        "- Use the console menu: Detalhes (shows this message).\n"
        "- For test mode only, set email.dry_run=true.\n"
    )
    LOGGER.error("Config error: %s", reason, extra={"category": "config"})
    return message


def _reject_extra_args(args: list[str]) -> None:
    if not args:
        return
    if args[0] in ("--version", "-V"):
        from . import __version_label__, __release_date__
        print(f"SentinelTray {__version_label__}  ({__release_date__})")
        raise SystemExit(0)
    if args[0] in ("--help", "-h"):
        print(
            "SentinelTray — monitor de janelas com alertas por e-mail.\n"
            "\n"
            "Uso: python main.py [--version | --help]\n"
            "  --version, -V   Exibe versão e encerra.\n"
            "  --help,    -h   Exibe esta ajuda e encerra.\n"
        )
        raise SystemExit(0)
    raise SystemExit(
        "Usage: run SentinelTray without arguments.\n"
        f"Arguments received: {' '.join(args)}"
    )


def _setup_boot_logging() -> None:
    if logging.getLogger().handlers:
        return
    try:
        log_root = get_user_log_dir()
        log_root.mkdir(parents=True, exist_ok=True)
        boot_log = log_root / "sentineltray_boot.log"
        setup_logging(
            str(boot_log),
            log_level="INFO",
            log_console_level="INFO",
            log_console_enabled=True,
            log_max_bytes=1_000_000,
            log_backup_count=3,
            log_run_files_keep=3,
            app_version=__version_label__,
            release_date=__release_date__,
            commit_hash="",
        )
    except Exception as exc:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).warning(
            "Boot logging unavailable; using stderr: %s",
            exc,
            extra={"category": "startup"},
        )


def _legacy_data_dir() -> Path | None:
    candidates: list[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "ZWave" / "SentinelTray" / "config")
    else:
        user_root = os.environ.get("USERPROFILE")
        if user_root:
            candidates.append(
                Path(user_root)
                / "AppData"
                / "Local"
                / "ZWave"
                / "Tmp"
                / "SentinelTray"
                / "Config"
            )
    candidates.append(get_project_root() / "config")
    for candidate in candidates:
        if (candidate / "config.local.yaml").exists():
            return candidate
    return None


def _migrate_legacy_config(local_path: Path) -> None:
    legacy_dir = _legacy_data_dir()
    if legacy_dir is None:
        return
    legacy_config = legacy_dir / "config.local.yaml"
    if not legacy_config.exists():
        return
    if local_path.exists():
        try:
            if local_path.read_text(encoding="utf-8").strip():
                return
        except Exception:
            return
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(legacy_config, local_path)
        LOGGER.info(
            "Migrated legacy config to project scope",
            extra={"category": "config", "legacy_path": str(legacy_config)},
        )
    except Exception as exc:
        LOGGER.warning(
            "Failed to migrate legacy config: %s",
            exc,
            extra={"category": "config"},
        )


def _run_startup_integrity_checks(local_path: Path) -> None:
    data_dir = local_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    log_root = get_user_log_dir()
    log_root.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_config(local_path)



def _clear_stored_smtp_password(index: int) -> None:
    env_key = f"SENTINELTRAY_SMTP_PASSWORD_{index}"
    if env_key in os.environ:
        os.environ.pop(env_key, None)
    secret_path = get_user_data_dir() / f"smtp_password_{index}.dpapi"
    if not secret_path.exists():
        return
    try:
        secret_path.unlink()
        LOGGER.info(
            "Cleared stored SMTP password for monitor %s",
            index,
            extra={"category": "config"},
        )
    except Exception as exc:
        LOGGER.warning(
            "Failed to clear stored SMTP password for monitor %s: %s",
            index,
            exc,
            extra={"category": "config"},
        )


def _validate_smtp_config(config: AppConfig) -> tuple[list[tuple[int, str]], list[str]]:
    auth_failures: list[tuple[int, str]] = []
    auth_messages: list[str] = []
    failures: list[str] = []
    if config.log_only_mode:
        return auth_failures, auth_messages
    for index, monitor in enumerate(config.monitors, start=1):
        email = monitor.email
        try:
            validate_smtp_credentials(email)
        except EmailAuthError as exc:
            auth_failures.append((index, email.smtp_username))
            auth_messages.append(f"monitor {index}: {exc}")
        except Exception as exc:
            failures.append(f"monitor {index}: {exc}")
    if failures:
        raise ValueError("SMTP validation failed: " + "; ".join(failures))
    return auth_failures, auth_messages


def _ensure_windows() -> None:
    if sys.platform == "win32":
        return
    LOGGER.error(
        "Unsupported platform: %s (SentinelTray requires Windows)",
        sys.platform,
        extra={"category": "startup"},
    )
    raise SystemExit("SentinelTray requires Windows.")


def _missing_smtp_passwords(config: AppConfig) -> list[tuple[int, str]]:
    missing: list[tuple[int, str]] = []
    global_password = os.environ.get("SENTINELTRAY_SMTP_PASSWORD", "").strip()
    for index, monitor in enumerate(config.monitors, start=1):
        username = str(monitor.email.smtp_username or "").strip()
        if not username:
            continue
        if str(monitor.email.smtp_password or "").strip():
            continue
        indexed_password = os.environ.get(f"SENTINELTRAY_SMTP_PASSWORD_{index}", "").strip()
        if indexed_password or global_password:
            continue
        missing.append((index, username))
    return missing


def _prompt_smtp_passwords(missing: list[tuple[int, str]]) -> None:
    if not missing:
        return
    for index, username in missing:
        while True:
            password = prompt_smtp_password_gui(username, index)
            if password is None:
                raise SystemExit("Senha SMTP não informada.")
            password = password.strip()
            if password:
                os.environ[f"SENTINELTRAY_SMTP_PASSWORD_{index}"] = password
                try:
                    secret_path = get_user_data_dir() / f"smtp_password_{index}.dpapi"
                    save_secret(secret_path, password)
                except Exception as exc:
                    LOGGER.warning(
                        "Failed to store SMTP password securely: %s",
                        exc,
                        extra={"category": "config"},
                    )
                break


def main() -> int:
    _setup_boot_logging()
    _ensure_single_instance()
    args = [arg for arg in sys.argv[1:] if arg]
    _reject_extra_args(args)

    local_path = get_user_data_dir() / "config.local.yaml"
    config = None
    config_error_message = None
    try:
        _ensure_windows()
        _run_startup_integrity_checks(local_path)
        _ensure_local_override(local_path)
        config = load_config(str(local_path))
        missing_passwords = _missing_smtp_passwords(config)
        if missing_passwords:
            _prompt_smtp_passwords(missing_passwords)
            config = load_config(str(local_path))
        auth_failures, auth_messages = _validate_smtp_config(config)
        if auth_failures:
            for index, _ in auth_failures:
                _clear_stored_smtp_password(index)
            _prompt_smtp_passwords(auth_failures)
            config = load_config(str(local_path))
            auth_failures, auth_messages = _validate_smtp_config(config)
            if auth_failures:
                raise ValueError(
                    "SMTP validation failed (SENTINELTRAY_SMTP_PASSWORD): "
                    + "; ".join(auth_messages)
                )
    except Exception as exc:
        config_error_message = _handle_config_error(local_path, exc)

    try:
        if config_error_message is not None:
            run_console_config_error(config_error_message)
        else:
            if config is None:
                raise SystemExit("Configuration not loaded.")
            run_gui(config)
    except Exception as exc:
        LOGGER.error("Failed to start console UI: %s", exc, extra={"category": "startup"})
        raise SystemExit("Failed to start console UI.") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
