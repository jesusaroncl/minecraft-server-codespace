#!/usr/bin/env python
# coding: utf-8

import subprocess
import sys
import os
import psutil
import requests
import time
import threading
import socket
from typing import Optional, List
from datetime import datetime
import pty
import glob
import shutil
import re

# =====================================================
# CONFIGURACIÓN Y CONSTANTES
# =====================================================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"

C = Colors()

class Config:
    BASE_DIR = os.path.abspath("Minecraft-servers")
    MC_PORT = 9005  # Cambiado de 25565 a 9005
    VERSION = "2.3"
    
    SERVER_TYPES = {
        "Vanilla": {"desc": "Minecraft puro", "icon": "🍦", "color": C.GRAY},
        "Forge": {"desc": "Para mods", "icon": "🔨", "color": C.YELLOW},
        "Fabric": {"desc": "Mods ligeros", "icon": "🧵", "color": C.GREEN},
        "Paper": {"desc": "Plugins rápido", "icon": "📄", "color": C.CYAN},
        "Purpur": {"desc": "Plugins+extras", "icon": "💜", "color": C.MAGENTA},
        "Mohist": {"desc": "Mods+Plugins", "icon": "🔥", "color": C.RED},
    }

os.makedirs(Config.BASE_DIR, exist_ok=True)

# =====================================================
# UI COMPONENTS
# =====================================================

def strip_ansi(text: str) -> str:
    """Elimina códigos ANSI para calcular longitud real."""
    return re.sub(r'\033\[[0-9;]*m', '', text)

def pad_ansi(text: str, width: int) -> str:
    """Padding que considera códigos ANSI."""
    visible_len = len(strip_ansi(text))
    padding = width - visible_len
    return text + " " * max(0, padding)

class UI:
    BOX_WIDTH = 57
    
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def banner():
        UI.clear()
        w = UI.BOX_WIDTH
        print()
        print(f"  {C.GREEN}╔{'═' * w}╗{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}                                                         {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}███╗   ███╗{C.RESET} {C.MAGENTA}██████╗{C.RESET}    {C.YELLOW}███████╗███████╗██████╗{C.RESET}    {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}████╗ ████║{C.RESET}{C.MAGENTA}██╔════╝{C.RESET}    {C.YELLOW}██╔════╝██╔════╝██╔══██╗{C.RESET}   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}██╔████╔██║{C.RESET}{C.MAGENTA}██║{C.RESET}         {C.YELLOW}███████╗█████╗  ██████╔╝{C.RESET}   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}██║╚██╔╝██║{C.RESET}{C.MAGENTA}██║{C.RESET}         {C.YELLOW}╚════██║██╔══╝  ██╔══██╗{C.RESET}   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}██║ ╚═╝ ██║{C.RESET}{C.MAGENTA}╚██████╗{C.RESET}    {C.YELLOW}███████║███████╗██║  ██║{C.RESET}   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.CYAN}╚═╝     ╚═╝{C.RESET} {C.MAGENTA}╚═════╝{C.RESET}    {C.YELLOW}╚══════╝╚══════╝╚═╝  ╚═╝{C.RESET}   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}                                                         {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}╠{'═' * w}╣{C.RESET}")
        title = f"🎮 Minecraft Server Manager v{Config.VERSION}"
        subtitle = "Optimizado para GitHub Codespaces"
        print(f"  {C.GREEN}║{C.RESET}   {C.BOLD}{title}{C.RESET}                        {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}║{C.RESET}   {C.DIM}{subtitle}{C.RESET}                   {C.GREEN}║{C.RESET}")
        print(f"  {C.GREEN}╚{'═' * w}╝{C.RESET}")
        print()

    @staticmethod
    def header(title: str, subtitle: str = ""):
        w = 50
        print()
        print(f"  {C.CYAN}┏{'━' * w}┓{C.RESET}")
        print(f"  {C.CYAN}┃{C.RESET}  {C.BOLD}{pad_ansi(title, w - 3)}{C.RESET}{C.CYAN}┃{C.RESET}")
        if subtitle:
            print(f"  {C.CYAN}┃{C.RESET}  {C.DIM}{pad_ansi(subtitle, w - 3)}{C.RESET}{C.CYAN}┃{C.RESET}")
        print(f"  {C.CYAN}┗{'━' * w}┛{C.RESET}")
        print()

    @staticmethod
    def box(lines: List[str], color: str = C.CYAN, width: int = 44):
        w = width
        print()
        print(f"  {color}┌{'─' * w}┐{C.RESET}")
        for line in lines:
            padded = pad_ansi(line, w - 2)
            print(f"  {color}│{C.RESET} {padded}{color}│{C.RESET}")
        print(f"  {color}└{'─' * w}┘{C.RESET}")
        print()

    @staticmethod
    def divider(char: str = "─", width: int = 50):
        print(f"  {C.DIM}{char * width}{C.RESET}")

    @staticmethod
    def table_row(cols: List[tuple], widths: List[int]):
        """Imprime una fila de tabla con columnas alineadas."""
        row = "  "
        for i, (text, color) in enumerate(cols):
            padded = pad_ansi(f"{color}{text}{C.RESET}", widths[i])
            row += padded
        print(row)

class Log:
    @staticmethod
    def _log(icon: str, msg: str, color: str):
        print(f"  {color}{icon}{C.RESET} {msg}")
    
    @staticmethod
    def success(msg: str): 
        Log._log("✓", msg, C.GREEN)
    
    @staticmethod
    def error(msg: str): 
        Log._log("✗", msg, C.RED)
    
    @staticmethod
    def warn(msg: str): 
        Log._log("⚠", msg, C.YELLOW)
    
    @staticmethod
    def info(msg: str): 
        Log._log("●", msg, C.CYAN)
    
    @staticmethod
    def ask(msg: str) -> str:
        return input(f"  {C.CYAN}›{C.RESET} {msg}")

class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    
    def __init__(self, msg: str):
        self.msg = msg
        self.running = False
        self.thread = None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop(not any(args))
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def _spin(self):
        i = 0
        while self.running:
            frame = self.FRAMES[i % len(self.FRAMES)]
            print(f"\r  {C.YELLOW}{frame}{C.RESET} {self.msg}...", end="", flush=True)
            time.sleep(0.08)
            i += 1
    
    def stop(self, success: bool = True):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.3)
        icon = f"{C.GREEN}✓{C.RESET}" if success else f"{C.RED}✗{C.RESET}"
        print(f"\r  {icon} {self.msg}                    ")

class Progress:
    @staticmethod
    def bar(current: int, total: int, width: int = 32):
        if not total:
            return
        pct = min(current / total, 1.0)
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        mb = current / 1048576
        total_mb = total / 1048576
        print(f"\r  {C.CYAN}│{bar}│{C.RESET} {pct*100:5.1f}% {C.DIM}({mb:.1f}/{total_mb:.1f} MB){C.RESET}", end="", flush=True)

# =====================================================
# DEPENDENCIAS
# =====================================================

def ensure_dependencies():
    pkgs = {"python-dotenv": "dotenv", "pytz": "pytz", "inquirer": "inquirer", "pyngrok": "pyngrok"}
    for pkg, module in pkgs.items():
        try:
            __import__(module)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ensure_dependencies()

import inquirer
from pyngrok import ngrok, conf
from dotenv import load_dotenv
load_dotenv()

# ===================== Keep-Alive opcional =====================
# Esta rutina está desactivada por defecto. Para activarla, exporta
# `KEEP_ALIVE=1` y opcionalmente `KEEP_ALIVE_URL` y
# `KEEP_ALIVE_INTERVAL_MIN` (intervalo en minutos, por defecto 4).
def keep_codespace_alive(interval_minutes: int = 4, url: str = "https://www.gstatic.com/generate_204"):
    """Lanza un hilo daemon que hace peticiones periódicas a `url`.

    Diseñado para generar actividad de red ligera y evitar que algunos
    entornos cierren la sesión por inactividad. Usa con precaución.
    """
    def _ping_loop():
        while True:
            try:
                # Petición muy ligera (204) para minimizar tráfico.
                requests.get(url, timeout=8)
                Log.info("Keep-alive: ping enviado")
            except Exception:
                # No queremos spam de errores en el log; avisamos de forma leve.
                Log.warn("Keep-alive: fallo al enviar ping (ignorado)")
            time.sleep(max(1, interval_minutes) * 60)

    t = threading.Thread(target=_ping_loop, daemon=True)
    t.start()
    return t

# =====================================================
# UTILIDADES DE RED
# =====================================================

class Network:
    _port_released = False
    
    @classmethod
    def is_port_busy(cls, port: int = Config.MC_PORT) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    @classmethod
    def release_port(cls, port: int = Config.MC_PORT):
        if cls._port_released:
            return
        if cls.is_port_busy(port):
            subprocess.run(f"fuser -k {port}/tcp", shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            Log.info(f"Puerto {port} liberado")
        cls._port_released = True
    
    @staticmethod
    def download(url: str, path: str) -> bool:
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            current = 0
            
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    current += len(chunk)
                    f.write(chunk)
                    Progress.bar(current, total)
            print()
            return True
        except Exception as e:
            Log.error(f"Descarga fallida: {e}")
            return False

# =====================================================
# TÚNELES
# =====================================================

class Tunnel:
    @staticmethod
    def _check_cmd(cmd: str) -> bool:
        return subprocess.run(["which", cmd], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL).returncode == 0
    
    @staticmethod
    def _kill_existing_tunnels():
        """Mata todos los procesos de túneles existentes para evitar duplicados."""
        tunnel_processes = ["playit", "cloudflared", "ngrok"]
        killed = False
        
        for proc_name in tunnel_processes:
            # Verificar si hay procesos corriendo
            result = subprocess.run(["pgrep", "-f", proc_name], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                # Matar los procesos
                subprocess.run(["pkill", "-9", "-f", proc_name],
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
                killed = True
        
        if killed:
            time.sleep(1)  # Esperar a que se cierren los procesos
            Log.info("Túneles anteriores cerrados")
        
        # También cerrar túneles de ngrok via API
        try:
            ngrok.kill()
        except:
            pass
    
    @staticmethod
    def get_available() -> List[str]:
        tunnels = []
        
        # Cloudflare (mejor opción)
        if Tunnel._check_cmd("cloudflared"):
            tunnels.append("☁️   Cloudflare Tunnel (Mejor)")
        else:
            tunnels.append("☁️   Instalar Cloudflare (Mejor)")
        
        # Ngrok
        if os.getenv("NGROK_AUTH_TOKEN"):
            tunnels.append("🌐  Ngrok (Estable)")
        
        # Playit
        if Tunnel._check_cmd("playit"):
            tunnels.append("🎮  Playit.gg")
        else:
            Tunnel._install_playit()
            if Tunnel._check_cmd("playit"):
                tunnels.append("🎮  Playit.gg")
        
        tunnels.append("🔌  Sin túnel (Local)")
        return tunnels
    
    @staticmethod
    def _install_playit():
        if Tunnel._check_cmd("playit"):
            return True
        
        with Spinner("Instalando Playit.gg"):
            try:
                cmds = [
                    "curl -SsL https://playit-cloud.github.io/ppa/key.gpg -o /tmp/key.gpg",
                    "sudo apt-key add /tmp/key.gpg 2>/dev/null",
                    "echo 'deb https://playit-cloud.github.io/ppa/data ./' | sudo tee /etc/apt/sources.list.d/playit-cloud.list >/dev/null",
                    "sudo apt update -qq",
                    "sudo apt install -y playit -qq"
                ]
                for cmd in cmds:
                    subprocess.run(cmd, shell=True, check=True,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except:
                return False
    
    @staticmethod
    def _install_cloudflare():
        if Tunnel._check_cmd("cloudflared"):
            return True
        
        with Spinner("Instalando Cloudflare Tunnel"):
            try:
                cmds = [
                    "curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb",
                    "sudo dpkg -i /tmp/cloudflared.deb"
                ]
                for cmd in cmds:
                    subprocess.run(cmd, shell=True, check=True,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except:
                return False
    
    @staticmethod
    def start(choice: str):
        # Primero cerrar cualquier túnel existente para evitar duplicados
        Tunnel._kill_existing_tunnels()
        
        Network.release_port()
        
        if "Cloudflare" in choice:
            return Tunnel._start_cloudflare()
        elif "Ngrok" in choice:
            return Tunnel._start_ngrok()
        elif "Playit" in choice:
            return Tunnel._start_playit()
        return None
    
    @staticmethod
    def _start_cloudflare():
        # Instalar si no existe
        if not Tunnel._check_cmd("cloudflared"):
            if not Tunnel._install_cloudflare():
                Log.error("No se pudo instalar Cloudflare")
                return None
        
        try:
            # Para TCP, cloudflared usa stderr para los logs
            proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"tcp://localhost:{Config.MC_PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print()
            Log.info("Iniciando Cloudflare Tunnel...")
            Log.info("Buscando dirección del túnel...")
            print()
            
            url_found = [False]  # Usar lista para modificar en closure
            tunnel_url = [None]
            
            def read_stderr():
                for line in proc.stderr:
                    # Cloudflare muestra la URL en stderr
                    if "trycloudflare.com" in line or "cfargotunnel.com" in line:
                        match = re.search(r'https?://([a-z0-9-]+\.trycloudflare\.com)', line)
                        if match:
                            tunnel_url[0] = match.group(1)
                            url_found[0] = True
                    # También buscar en formato TCP
                    if "tcp://" in line.lower() and "trycloudflare" in line:
                        match = re.search(r'([a-z0-9-]+\.trycloudflare\.com:\d+)', line)
                        if match:
                            tunnel_url[0] = match.group(1)
                            url_found[0] = True
                    # Imprimir logs relevantes
                    if "registered" in line.lower() or "connection" in line.lower():
                        print(f"  {C.DIM}{line.strip()}{C.RESET}")
            
            def read_stdout():
                for line in proc.stdout:
                    if "trycloudflare.com" in line:
                        match = re.search(r'([a-z0-9-]+\.trycloudflare\.com)', line)
                        if match:
                            tunnel_url[0] = match.group(1)
                            url_found[0] = True
            
            # Leer ambos streams
            t1 = threading.Thread(target=read_stderr, daemon=True)
            t2 = threading.Thread(target=read_stdout, daemon=True)
            t1.start()
            t2.start()
            
            # Esperar hasta 15 segundos por la URL
            for i in range(30):
                if url_found[0]:
                    break
                time.sleep(0.5)
                if i % 4 == 0:
                    print(f"\r  {C.YELLOW}{'.' * ((i//4) % 4 + 1):<4}{C.RESET} Conectando...", end="", flush=True)
            
            print("\r" + " " * 30 + "\r", end="")  # Limpiar línea
            
            if url_found[0] and tunnel_url[0]:
                UI.box([
                    f"{C.BOLD}☁️  Cloudflare Tunnel Activo{C.RESET}",
                    f"",
                    f"  Dirección: {C.GREEN}{C.BOLD}{tunnel_url[0]}{C.RESET}",
                    f"",
                    f"{C.DIM}  Copia esta dirección en Minecraft{C.RESET}",
                    f"{C.DIM}  (Añadir servidor → pegar dirección){C.RESET}",
                ], C.GREEN, 50)
            else:
                # Si no encontró URL automáticamente, mostrar alternativa
                Log.warn("No se detectó la URL automáticamente")
                print()
                UI.box([
                    f"{C.BOLD}☁️  Cloudflare Tunnel Iniciado{C.RESET}",
                    f"",
                    f"  {C.YELLOW}Busca la URL en los logs de arriba{C.RESET}",
                    f"  {C.DIM}Formato: xxx-xxx.trycloudflare.com{C.RESET}",
                    f"",
                    f"  {C.DIM}O ejecuta en otra terminal:{C.RESET}",
                    f"  {C.CYAN}cloudflared tunnel --url tcp://localhost:25565{C.RESET}",
                ], C.YELLOW, 55)
            
            return proc
            
        except Exception as e:
            Log.error(f"Error Cloudflare: {e}")
            return None
    
    @staticmethod
    def _start_playit():
        try:
            proc = subprocess.Popen(
                ["playit", "run"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            print()
            UI.box([
                f"{C.BOLD}🎮  Playit.gg Activo{C.RESET}",
                f"",
                f"{C.DIM}  Ejecuta 'playit' en otra terminal{C.RESET}",
                f"{C.DIM}  para ver tu dirección IP{C.RESET}",
            ], C.CYAN, 42)
            return proc
        except Exception as e:
            Log.error(f"Error Playit: {e}")
            return None
    
    @staticmethod
    def _start_ngrok():
        try:
            token = os.getenv("NGROK_AUTH_TOKEN")
            region = os.getenv("NGROK_REGION", "us")
            
            ngrok.set_auth_token(token)
            conf.get_default().region = region
            tunnel = ngrok.connect(Config.MC_PORT, "tcp")
            
            url = str(tunnel).split('"')[1].replace('tcp://', '')
            print()
            UI.box([
                f"{C.BOLD}🌐  Ngrok Activo{C.RESET}",
                f"",
                f"  Dirección: {C.GREEN}{C.BOLD}{url}{C.RESET}",
                f"",
                f"{C.DIM}  Copia la dirección en Minecraft{C.RESET}",
            ], C.GREEN, 48)
            return tunnel
        except Exception as e:
            Log.error(f"Error Ngrok: {e}")
            return None

# =====================================================
# SERVIDOR
# =====================================================

class Server:
    @staticmethod
    def get_all() -> List[str]:
        if not os.path.exists(Config.BASE_DIR):
            return []
        return [d for d in os.listdir(Config.BASE_DIR) 
                if os.path.isdir(os.path.join(Config.BASE_DIR, d))]
    
    @staticmethod
    def get_info(name: str) -> dict:
        path = os.path.join(Config.BASE_DIR, name)
        info = {"type": "Vanilla", "mods": 0, "plugins": 0, "world": False}
        
        if os.path.exists(os.path.join(path, "run.sh")):
            info["type"] = "Forge"
        else:
            for f in os.listdir(path):
                if f.endswith(".jar") and "installer" not in f.lower():
                    fl = f.lower()
                    for t in Config.SERVER_TYPES:
                        if t.lower() in fl:
                            info["type"] = t
                            break
                    break
        
        mods_path = os.path.join(path, "mods")
        plugins_path = os.path.join(path, "plugins")
        
        if os.path.exists(mods_path):
            info["mods"] = len([f for f in os.listdir(mods_path) if f.endswith(".jar")])
        if os.path.exists(plugins_path):
            info["plugins"] = len([f for f in os.listdir(plugins_path) if f.endswith(".jar")])
        
        info["world"] = os.path.exists(os.path.join(path, "world"))
        return info
    
    @staticmethod
    def display_list() -> List[str]:
        servers = Server.get_all()
        if not servers:
            return servers
        
        UI.header("📂 Servidores Disponibles")
        
        print(f"  {C.DIM}{'─' * 50}{C.RESET}")
        
        for name in servers:
            info = Server.get_info(name)
            type_cfg = Config.SERVER_TYPES.get(info["type"], {"icon": "📦", "color": C.GRAY})
            
            # Iconos
            world_icon = "🌍" if info["world"] else "🆕"
            
            # Extras
            extras = []
            if info["mods"]: 
                extras.append(f"{info['mods']} mods")
            if info["plugins"]: 
                extras.append(f"{info['plugins']} plugins")
            extra_str = f"{C.DIM}({', '.join(extras)}){C.RESET}" if extras else ""
            
            # Formato de tipo
            type_str = f"{type_cfg['color']}[{type_cfg['icon']} {info['type']:<7}]{C.RESET}"
            
            print(f"  {world_icon} {C.BOLD}{name:<16}{C.RESET}  {type_str}  {extra_str}")
        
        print(f"  {C.DIM}{'─' * 50}{C.RESET}")
        print()
        return servers

# =====================================================
# VERSIONES Y DESCARGAS
# =====================================================

class Versions:
    CACHE = {}
    
    @classmethod
    def get(cls, server_type: str) -> List[str]:
        if server_type in cls.CACHE:
            return cls.CACHE[server_type]
        
        fetchers = {
            "Vanilla": cls._minecraft,
            "Paper": cls._minecraft,
            "Purpur": cls._minecraft,
            "Fabric": cls._minecraft,
            "Forge": cls._forge,
            "Mohist": cls._mohist,
        }
        
        versions = fetchers.get(server_type, cls._minecraft)()
        cls.CACHE[server_type] = versions
        return versions
    
    @staticmethod
    def _minecraft() -> List[str]:
        try:
            r = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json", timeout=10)
            return [v["id"] for v in r.json()["versions"] if v["type"] == "release"][:15]
        except:
            return ["1.20.4", "1.20.2", "1.20.1", "1.19.4", "1.18.2"]
    
    @staticmethod
    def _forge() -> List[str]:
        try:
            r = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json", timeout=10)
            versions = set()
            for key in r.json().get("promos", {}):
                v = key.replace("-recommended", "").replace("-latest", "")
                versions.add(v)
            return sorted(versions, key=lambda x: [int(n) if n.isdigit() else 0 for n in x.split(".")], reverse=True)[:15]
        except:
            return Versions._minecraft()[:10]
    
    @staticmethod
    def _mohist() -> List[str]:
        try:
            r = requests.get("https://mohistmc.com/api/v2/projects/mohist", timeout=10)
            v = r.json().get("versions", [])
            v.reverse()
            return v[:15]
        except:
            return []

class Downloads:
    @staticmethod
    def get_url(server_type: str, version: str) -> Optional[str]:
        handlers = {
            "Vanilla": Downloads._vanilla,
            "Forge": Downloads._forge,
            "Paper": Downloads._paper,
            "Fabric": Downloads._fabric,
            "Mohist": Downloads._mohist,
            "Purpur": Downloads._purpur,
        }
        return handlers.get(server_type, lambda v: None)(version)
    
    @staticmethod
    def _vanilla(version: str) -> Optional[str]:
        try:
            r = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
            url = next((v["url"] for v in r.json()["versions"] if v["id"] == version), None)
            return requests.get(url).json()["downloads"]["server"]["url"] if url else None
        except:
            return None
    
    @staticmethod
    def _forge(version: str) -> Optional[str]:
        try:
            base = "https://maven.minecraftforge.net/net/minecraftforge/forge"
            r = requests.get(f"{base}/maven-metadata.xml")
            versions = [v.split('</version>')[0] for v in r.text.split('<version>')[1:]]
            match = [v for v in versions if v.startswith(version)]
            if match:
                latest = max(match, key=lambda v: [int(x) if x.isdigit() else 0 for x in v.replace("-", ".").split(".")])
                return f"{base}/{latest}/forge-{latest}-installer.jar"
        except:
            pass
        return None
    
    @staticmethod
    def _paper(version: str) -> Optional[str]:
        try:
            r = requests.get(f"https://papermc.io/api/v2/projects/paper/versions/{version}")
            builds = r.json().get('builds', [])
            if builds:
                b = builds[-1]
                return f"https://papermc.io/api/v2/projects/paper/versions/{version}/builds/{b}/downloads/paper-{version}-{b}.jar"
        except:
            pass
        return None
    
    @staticmethod
    def _fabric(version: str) -> Optional[str]:
        try:
            loader = requests.get("https://meta.fabricmc.net/v2/versions/loader").json()
            installer = requests.get("https://meta.fabricmc.net/v2/versions/installer").json()
            lv = next((v["version"] for v in loader if v.get("stable")), None)
            iv = next((v["version"] for v in installer if v.get("stable")), None)
            if lv and iv:
                return f"https://meta.fabricmc.net/v2/versions/loader/{version}/{lv}/{iv}/server/jar"
        except:
            pass
        return None
    
    @staticmethod
    def _mohist(version: str) -> Optional[str]:
        try:
            r = requests.get(f"https://mohistmc.com/api/v2/projects/mohist/{version}/builds")
            return r.json()["builds"][-1]["url"]
        except:
            return None
    
    @staticmethod
    def _purpur(version: str) -> Optional[str]:
        try:
            r = requests.get(f"https://api.purpurmc.org/v2/purpur/{version}")
            b = r.json()["builds"]["latest"]
            return f"https://api.purpurmc.org/v2/purpur/{version}/{b}/download"
        except:
            return None

# =====================================================
# ACCIONES PRINCIPALES
# =====================================================

def create_server() -> Optional[str]:
    UI.header("📦 Crear Nuevo Servidor")
    
    name = Log.ask("Nombre del servidor: ").strip()
    if not name:
        Log.error("El nombre es requerido")
        return None
    
    if name in Server.get_all():
        Log.error("Ya existe un servidor con ese nombre")
        return None
    
    print()
    type_choices = [f"{v['icon']}  {k:<8} │ {v['desc']}" for k, v in Config.SERVER_TYPES.items()]
    answer = inquirer.prompt([inquirer.List('type', message="Tipo de servidor", choices=type_choices)])
    if not answer:
        return None
    server_type = answer['type'].split()[1]
    
    print()
    with Spinner("Obteniendo versiones disponibles"):
        versions = Versions.get(server_type)
    
    if not versions:
        Log.error("No se pudieron obtener las versiones")
        return None
    
    answer = inquirer.prompt([inquirer.List('ver', message="Versión de Minecraft", choices=versions)])
    if not answer:
        return None
    version = answer['ver']
    
    type_cfg = Config.SERVER_TYPES[server_type]
    UI.box([
        f"{C.BOLD}╔══ Resumen de Configuración ══╗{C.RESET}",
        f"",
        f"  📛  Nombre:   {C.GREEN}{C.BOLD}{name}{C.RESET}",
        f"  {type_cfg['icon']}   Tipo:     {type_cfg['color']}{server_type}{C.RESET}",
        f"  📦  Versión:  {C.BLUE}{version}{C.RESET}",
        f"",
    ], width=40)
    
    confirm = inquirer.prompt([inquirer.Confirm('ok', message="¿Confirmar creación?", default=True)])
    if not confirm or not confirm['ok']:
        Log.warn("Operación cancelada")
        return None
    
    server_dir = os.path.join(Config.BASE_DIR, name)
    os.makedirs(server_dir, exist_ok=True)
    
    url = Downloads.get_url(server_type, version)
    if not url:
        Log.error("No se encontró URL de descarga")
        shutil.rmtree(server_dir)
        return None
    
    print()
    Log.info(f"Descargando {server_type} {version}...")
    
    if server_type == "Forge":
        installer = os.path.join(server_dir, "installer.jar")
        if not Network.download(url, installer):
            shutil.rmtree(server_dir)
            return None
        
        with Spinner("Instalando Forge (esto puede tardar)"):
            result = subprocess.run(
                ["java", "-jar", installer, "--installServer"],
                cwd=server_dir, capture_output=True
            )
        
        if result.returncode != 0:
            Log.error("Error al instalar Forge")
            shutil.rmtree(server_dir)
            return None
        
        try:
            os.remove(installer)
        except:
            pass
    else:
        if not Network.download(url, os.path.join(server_dir, "server.jar")):
            shutil.rmtree(server_dir)
            return None
    
    with open(os.path.join(server_dir, 'eula.txt'), 'w') as f:
        f.write('eula=true\n')
    
    props = {
        "server-name": name,
        "motd": f"\\u00A7b{name} \\u00A77- \\u00A7aOnline",
        "gamemode": "survival",
        "difficulty": "hard",
        "max-players": "20",
        "view-distance": "10",
        "spawn-protection": "0",
        "online-mode": "false",
        "enable-command-block": "true"
    }
    with open(os.path.join(server_dir, 'server.properties'), 'w') as f:
        f.writelines(f"{k}={v}\n" for k, v in props.items())
    
    print()
    Log.success(f"Servidor '{name}' creado exitosamente!")
    return name

def delete_server():
    UI.header("🗑️  Eliminar Servidor")
    
    servers = Server.get_all()
    if not servers:
        Log.warn("No hay servidores disponibles")
        return
    
    choices = servers + ["", "↩️  Cancelar"]
    answer = inquirer.prompt([inquirer.List('s', message="Selecciona servidor", choices=choices)])
    
    if not answer or answer['s'] == "↩️  Cancelar" or answer['s'] == "":
        return
    
    confirm = inquirer.prompt([
        inquirer.Confirm('ok', message=f"⚠️  ¿Eliminar '{answer['s']}' permanentemente?", default=False)
    ])
    
    if confirm and confirm['ok']:
        shutil.rmtree(os.path.join(Config.BASE_DIR, answer['s']))
        Log.success("Servidor eliminado correctamente")

def run_server(name: str):
    server_dir = os.path.join(Config.BASE_DIR, name)
    os.chdir(server_dir)
    
    UI.header("🌐 Configurar Túnel")
    tunnels = Tunnel.get_available()
    answer = inquirer.prompt([inquirer.List('t', message="Método de conexión", choices=tunnels)])
    if not answer:
        return
    tunnel_proc = Tunnel.start(answer['t'])
    
    UI.header("⚡ Iniciar Servidor", name)
    
    total_ram = psutil.virtual_memory().total // (1024 ** 3)
    default_ram = max(2, int(total_ram * 0.75))
    
    print(f"  {C.DIM}RAM del sistema: {total_ram}GB{C.RESET}")
    print(f"  {C.DIM}Recomendado: {default_ram}GB (75%){C.RESET}")
    print()
    
    ram_input = Log.ask(f"RAM a usar [{default_ram}GB]: ").strip()
    ram = int(ram_input) if ram_input.isdigit() else default_ram
    
    print()
    Log.info(f"Iniciando servidor con {ram}GB de RAM...")
    UI.divider("─", 50)
    print()
    
    if os.path.exists("run.sh"):
        with open("user_jvm_args.txt", "w") as f:
            f.write(f"-Xms{min(2, ram)}G\n-Xmx{ram}G\n")
        cmd = ["bash", "run.sh", "nogui"]
    else:
        jars = [j for j in glob.glob("*.jar") if "installer" not in j.lower()]
        jar = next((j for j in jars if any(x in j.lower() for x in 
                   ["server", "paper", "fabric", "mohist", "purpur", "forge"])), 
                   jars[0] if jars else None)
        
        if not jar:
            Log.error("No se encontró el JAR del servidor")
            return
        
        cmd = ["java", f"-Xms{min(2, ram)}G", f"-Xmx{ram}G", "-jar", jar, "nogui"]
    
    master, slave = pty.openpty()
    proc = subprocess.Popen(cmd, stdout=slave, stderr=slave, universal_newlines=True)
    os.close(slave)
    
    def monitor():
        while True:
            try:
                data = os.read(master, 4096).decode()
                if data:
                    print(data, end="", flush=True)
                else:
                    break
            except OSError:
                break
    
    threading.Thread(target=monitor, daemon=True).start()
    
    try:
        proc.wait()
    except KeyboardInterrupt:
        print()
        Log.warn("Deteniendo servidor...")
    finally:
        try:
            os.close(master)
        except:
            pass
        if tunnel_proc:
            tunnel_proc.terminate()
            Log.info("Túnel cerrado")

# =====================================================
# MAIN
# =====================================================

def main():
    # Activar keep-alive sólo si la variable de entorno lo indica.
    if os.getenv("KEEP_ALIVE", "").lower() in ("1", "true", "yes"):
        url = os.getenv("KEEP_ALIVE_URL", "https://www.gstatic.com/generate_204")
        try:
            interval = int(os.getenv("KEEP_ALIVE_INTERVAL_MIN", "50"))
        except Exception:
            interval = 4
        keep_codespace_alive(interval_minutes=interval, url=url)
        Log.info(f"Keep-alive activado cada {interval} minutos -> {url}")

    UI.banner()
    servers = Server.display_list()
    
    if servers:
        choices = servers + [
            "",
            "📦  Crear nuevo servidor",
            "🗑️   Eliminar servidor",
            "❌  Salir"
        ]
    else:
        Log.info("No hay servidores. ¡Crea tu primero!")
        print()
        choices = [
            "📦  Crear nuevo servidor",
            "❌  Salir"
        ]
    
    answer = inquirer.prompt([inquirer.List('a', message="¿Qué deseas hacer?", choices=choices)])
    
    if not answer:
        return
    
    action = answer['a']
    
    if action == "" or action.startswith("─"):
        return main()
    elif action == "❌  Salir":
        print()
        Log.info("¡Hasta pronto! 👋")
    elif action == "📦  Crear nuevo servidor":
        server = create_server()
        if server:
            print()
            start = inquirer.prompt([inquirer.Confirm('start', message="¿Iniciar servidor ahora?", default=True)])
            if start and start['start']:
                run_server(server)
            else:
                main()
        else:
            main()
    elif action == "🗑️   Eliminar servidor":
        delete_server()
        main()
    else:
        run_server(action)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        Log.info("¡Hasta pronto! 👋")
    except Exception as e:
        Log.error(f"Error inesperado: {e}")
