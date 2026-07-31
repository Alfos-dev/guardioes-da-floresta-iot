"""
Flash Service - Gravação de firmware no ESP32 via servidor (Fase 6)

Permite gravar o firmware compilado (Fase 4) diretamente no ESP32 conectado
via USB à porta serial do servidor, usando esptool. O flash ocorre no servidor
(não no navegador do usuário), portanto funciona em qualquer navegador e sem HTTPS.
"""

import re
import sys
import uuid
import threading
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field

try:
    import serial.tools.list_ports as list_ports
    _HAS_PYSERIAL = True
except Exception:  # pragma: no cover - pyserial pode não estar instalado em dev
    list_ports = None
    _HAS_PYSERIAL = False

from firmware_builder import FirmwareBuilder


# Padrões de hardware que indicam adaptadores USB-Serial comuns em placas ESP32
_USB_SERIAL_HINTS = ("USB", "UART", "CP210", "CH340", "CH910", "FTDI", "ACM", "SERIAL")

# Padrão para detectar progresso na saída do esptool: "Writing at 0x... (12 %)"
_PROGRESS_RE = re.compile(r"\((\d{1,3})\s*%\)")


@dataclass
class FlashJob:
    """Representa um trabalho de gravação de firmware"""
    flash_id: str
    build_id: str
    device_id: str
    port: str
    status: str = "pending"          # "pending" | "running" | "success" | "error"
    progress: int = 0                # 0-100
    log_lines: List[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "flash_id": self.flash_id,
            "build_id": self.build_id,
            "device_id": self.device_id,
            "port": self.port,
            "status": self.status,
            "progress": self.progress,
            "log_lines": self.log_lines,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class FlashError(Exception):
    """Erro ao iniciar/executar o flash"""
    pass


class FlashService:
    """Gerencia a gravação de firmware nos dispositivos ESP32 via USB"""

    def __init__(self, firmware_builder: FirmwareBuilder):
        self.firmware_builder = firmware_builder
        self.jobs: Dict[str, FlashJob] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------------- ports
    def list_ports(self) -> List[Dict]:
        """
        Lista portas seriais disponíveis no servidor.
        Retorna apenas portas que parecem ser adaptadores USB-Serial.
        """
        if not _HAS_PYSERIAL or list_ports is None:
            return []

        ports = []
        for p in list_ports.comports():
            haystack = " ".join(
                str(x or "").upper()
                for x in (p.device, p.description, p.hwid)
            )
            if any(hint in haystack for hint in _USB_SERIAL_HINTS):
                ports.append({
                    "port": p.device,
                    "description": p.description or p.device,
                    "hwid": p.hwid or "",
                })

        # Fallback: se nada casou com os hints mas há portas, retorna todas
        if not ports:
            for p in list_ports.comports():
                ports.append({
                    "port": p.device,
                    "description": p.description or p.device,
                    "hwid": p.hwid or "",
                })

        return ports

    # ----------------------------------------------------------------- start
    def start_flash(self, build_id: str, port: str, baud: int = 460800) -> str:
        """
        Inicia a gravação em uma thread separada e retorna o flash_id.
        Valida a existência do build e do arquivo .bin antes de iniciar.
        """
        if not port:
            raise FlashError("Porta serial não informada")

        build_info = self.firmware_builder.get_build_info(build_id)
        if not build_info:
            raise FlashError(f"Build não encontrado: {build_id}")

        firmware_path = self.firmware_builder.get_firmware_path(build_id)
        if not firmware_path or not firmware_path.exists():
            raise FlashError("Arquivo de firmware (.bin) não encontrado para este build")

        flash_id = str(uuid.uuid4())[:8]
        job = FlashJob(
            flash_id=flash_id,
            build_id=build_id,
            device_id=build_info.get("device_id", ""),
            port=port,
            status="pending",
            started_at=datetime.utcnow().isoformat(),
        )

        with self._lock:
            self.jobs[flash_id] = job

        thread = threading.Thread(
            target=self._run_flash,
            args=(flash_id, port, int(baud), str(firmware_path)),
            daemon=True,
        )
        thread.start()

        return flash_id

    # ------------------------------------------------------------------- run
    def _append_log(self, job: FlashJob, line: str):
        line = line.rstrip("\n").rstrip("\r")
        if line:
            job.log_lines.append(line)
            # Limita o histórico de log para evitar crescimento indefinido
            if len(job.log_lines) > 500:
                job.log_lines = job.log_lines[-500:]

    def _run_flash(self, flash_id: str, port: str, baud: int, firmware_path: str):
        """Executa o esptool e acompanha o progresso (roda em thread separada)"""
        job = self.jobs[flash_id]
        job.status = "running"
        job.progress = 0

        cmd = [
            sys.executable, "-m", "esptool",
            "--chip", "auto",
            "--port", port,
            "--baud", str(baud),
            "write_flash", "-z", "0x0", firmware_path,
        ]

        self._append_log(job, f"$ {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for raw_line in iter(process.stdout.readline, ""):
                if raw_line == "":
                    break
                self._append_log(job, raw_line)

                # Atualiza progresso ao encontrar "(NN %)"
                match = _PROGRESS_RE.search(raw_line)
                if match:
                    pct = int(match.group(1))
                    if pct > job.progress:
                        job.progress = min(pct, 99)

                # Marcos textuais do esptool
                low = raw_line.lower()
                if "hash of data verified" in low or "verifying" in low:
                    job.progress = max(job.progress, 95)

            process.stdout.close()
            returncode = process.wait(timeout=10)

            if returncode == 0:
                job.progress = 100
                job.status = "success"
                self._append_log(job, "[OK] Gravação concluída com sucesso.")
            else:
                job.status = "error"
                job.error = f"esptool terminou com código {returncode}"
                self._append_log(job, f"[ERRO] {job.error}")

        except FileNotFoundError:
            job.status = "error"
            job.error = "esptool não encontrado no servidor"
            self._append_log(job, f"[ERRO] {job.error}")
        except subprocess.TimeoutExpired:
            job.status = "error"
            job.error = "Timeout ao aguardar término do esptool"
            self._append_log(job, f"[ERRO] {job.error}")
        except Exception as e:
            job.status = "error"
            job.error = str(e)
            self._append_log(job, f"[ERRO] {job.error}")
        finally:
            job.finished_at = datetime.utcnow().isoformat()

    # ------------------------------------------------------------------- get
    def get_job(self, flash_id: str) -> Optional[FlashJob]:
        """Retorna o FlashJob pelo ID"""
        return self.jobs.get(flash_id)
