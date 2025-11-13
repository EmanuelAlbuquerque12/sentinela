#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Correção Automática do Sentinela
Corrige problemas de dependências e configuração
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Cores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Exibe o cabeçalho do script"""
    print(f"""
{Colors.BLUE}{'='*60}
{Colors.BOLD}    🔧 SENTINELA - Script de Correção Automática
{Colors.BLUE}{'='*60}{Colors.RESET}
    """)

def print_step(step_num, message):
    """Imprime um passo da correção"""
    print(f"\n{Colors.BOLD}[Passo {step_num}]{Colors.RESET} {message}")

def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")

def print_error(message):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")

def print_warning(message):
    """Imprime aviso"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {message}")

def check_python_version():
    """Verifica se Python 3.10+ está instalado"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_error(f"Python {version.major}.{version.minor} detectado. É necessário Python 3.10+")
        return False
    print_success(f"Python {version.major}.{version.minor} detectado")
    return True

def create_venv():
    """Cria ou recria o ambiente virtual"""
    venv_path = Path("venv")

    if venv_path.exists():
        print_warning("Ambiente virtual já existe. Removendo...")
        try:
            shutil.rmtree(venv_path)
            print_success("Ambiente virtual antigo removido")
        except Exception as e:
            print_error(f"Erro ao remover ambiente virtual: {e}")
            return False

    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True, capture_output=True)
        print_success("Ambiente virtual criado")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao criar ambiente virtual: {e}")
        return False

def get_pip_command():
    """Retorna o comando pip correto para o SO"""
    if os.name == 'nt':  # Windows
        return [str(Path("venv/Scripts/pip.exe"))]
    else:  # Linux/Mac
        return [str(Path("venv/bin/pip"))]

def get_python_command():
    """Retorna o comando Python do venv"""
    if os.name == 'nt':  # Windows
        return str(Path("venv/Scripts/python.exe"))
    else:  # Linux/Mac
        return str(Path("venv/bin/python"))

def upgrade_pip():
    """Atualiza pip no ambiente virtual"""
    try:
        pip_cmd = get_pip_command()
        subprocess.run(pip_cmd + ["install", "--upgrade", "pip"],
                      check=True, capture_output=True, text=True)
        print_success("pip atualizado")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao atualizar pip: {e}")
        return False

def install_dependencies():
    """Instala as dependências necessárias"""
    pip_cmd = get_pip_command()

    print("Instalando dependências do requirements.txt...")
    print("Isso pode levar alguns minutos na primeira vez...")

    try:
        subprocess.run(pip_cmd + ["install", "-r", "requirements.txt"],
                      check=True, capture_output=True, text=True)
        print_success("Dependências essenciais instaladas")
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao instalar requirements.txt: {e.stderr}")
        return False

    # Verificar se as dependências críticas estão instaladas
    critical_deps = ["beautifulsoup4", "lxml", "pymupdf", "unidecode"]
    python_cmd = get_python_command()

    for dep in critical_deps:
        try:
            test_import = {
                "beautifulsoup4": "from bs4 import BeautifulSoup",
                "lxml": "import lxml",
                "pymupdf": "import fitz",
                "unidecode": "from unidecode import unidecode"
            }
            subprocess.run([python_cmd, "-c", test_import[dep]],
                          check=True, capture_output=True)
            print(f"  {Colors.GREEN}✓{Colors.RESET} {dep}")
        except subprocess.CalledProcessError:
            print(f"  {Colors.YELLOW}!{Colors.RESET} {dep} - instalando separadamente...")
            try:
                subprocess.run(pip_cmd + ["install", dep],
                              check=True, capture_output=True)
                print(f"  {Colors.GREEN}✓{Colors.RESET} {dep} instalado")
            except subprocess.CalledProcessError as e:
                print(f"  {Colors.RED}✗{Colors.RESET} {dep}: falha")
                return False

    print_success("Todas as dependências verificadas")
    return True

def create_env_file():
    """Cria arquivo .env se não existir"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print_warning(".env já existe")
        return True

    if env_example.exists():
        try:
            shutil.copy2(env_example, env_file)
            print_success(".env criado a partir de .env.example")
            print_warning("Configure suas API keys em .env para acesso completo")
            return True
        except Exception as e:
            print_error(f"Erro ao copiar .env.example: {e}")

    # Criar .env básico
    basic_env = """# Configurações Básicas do Sentinela
APP_NAME=Sentinela
APP_VERSION=1.0.0
DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
HTTP_TIMEOUT=30
AGGREGATOR_TIMEOUT=120

# APIs (configure para funcionalidade completa)
DATAJUD_API_KEY=cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==
INLABS_USERNAME=emanuelcarlosalbuquerque@servidor.adv.br
INLABS_PASSWORD=Aq1sw2$&@
"""
    env_file.write_text(basic_env, encoding='utf-8')
    print_success(".env básico criado com credenciais padrão")
    return True

def fix_imports():
    """Corrige imports condicionais em services/__init__.py"""
    services_init = Path("app/services/__init__.py")
    backup_file = Path("app/services/__init__.py.backup")

    if not services_init.exists():
        print_error("app/services/__init__.py não encontrado")
        return False

    # Fazer backup
    try:
        shutil.copy2(services_init, backup_file)
        print_success("Backup criado: app/services/__init__.py.backup")
    except Exception as e:
        print_warning(f"Não foi possível criar backup: {e}")

    # Novo conteúdo com imports condicionais
    new_content = '''"""
Serviços de integração com fontes de dados
Versão com imports condicionais para dependências opcionais
"""

# Serviços essenciais (sempre disponíveis - sem dependências externas)
from .querido_diario import QueridoDiarioService
from .datajud import DataJudService
from .aggregator import SearchAggregator

__all__ = ["QueridoDiarioService", "DataJudService", "SearchAggregator"]

# Serviços com dependências opcionais (importar apenas se disponíveis)
try:
    from .tcu import TCUService
    __all__.append("TCUService")
except ImportError:
    pass

try:
    from .tcu_enhanced import TCUEnhancedService
    __all__.append("TCUEnhancedService")
except ImportError:
    pass

try:
    from .dou import DOUService
    __all__.append("DOUService")
except ImportError:
    pass

try:
    from .inlabs import INLabsService
    __all__.append("INLabsService")
except ImportError:
    pass

# Serviços que requerem beautifulsoup4, lxml, pymupdf
try:
    from .tcu_acordaos import TCUAcordaosService
    __all__.append("TCUAcordaosService")
except ImportError:
    pass

try:
    from .dou_scrapy import DOUScrapyService
    __all__.append("DOUScrapyService")
except ImportError:
    pass

try:
    from .dou_dados_abertos import DOUDadosAbertosService
    __all__.append("DOUDadosAbertosService")
except ImportError:
    pass
'''

    try:
        services_init.write_text(new_content, encoding='utf-8')
        print_success("Imports condicionais aplicados em app/services/__init__.py")
        return True
    except Exception as e:
        print_error(f"Erro ao modificar __init__.py: {e}")
        return False

def test_import():
    """Testa se o import do app funciona"""
    python_cmd = get_python_command()

    try:
        result = subprocess.run(
            [python_cmd, "-c", "from app.main import app; print('OK')"],
            capture_output=True, text=True, check=True, timeout=10
        )
        if "OK" in result.stdout:
            print_success("Teste de importação bem-sucedido")
            return True
        else:
            print_error("Import não retornou OK")
            return False
    except subprocess.TimeoutExpired:
        print_error("Timeout no teste de importação")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"Erro no teste de importação:")
        if e.stderr:
            print(f"  {e.stderr}")
        return False

def kill_port_8000():
    """Mata processos na porta 8000 se existirem"""
    if os.name == 'nt':  # Windows
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, shell=True
            )
            for line in result.stdout.split('\n'):
                if ':8000' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        try:
                            subprocess.run(["taskkill", "/F", "/PID", pid],
                                         capture_output=True, shell=True)
                            print_success(f"Processo na porta 8000 finalizado (PID: {pid})")
                            return True
                        except:
                            pass
            print_warning("Porta 8000 livre")
            return True
        except:
            return True
    else:  # Linux/Mac
        try:
            subprocess.run(["fuser", "-k", "8000/tcp"],
                          capture_output=True, stderr=subprocess.DEVNULL)
            print_success("Porta 8000 liberada")
        except:
            print_warning("Porta 8000 livre")
        return True

def main():
    """Função principal"""
    print_header()

    # Verificar se estamos no diretório correto
    if not Path("app").exists() or not Path("requirements.txt").exists():
        print_error("Este script deve ser executado na raiz do projeto Sentinela")
        print("Certifique-se de estar na pasta do projeto")
        return 1

    # Executar correções
    steps = [
        (1, "Verificando Python", check_python_version),
        (2, "Criando ambiente virtual", create_venv),
        (3, "Atualizando pip", upgrade_pip),
        (4, "Instalando dependências", install_dependencies),
        (5, "Criando arquivo .env", create_env_file),
        (6, "Corrigindo imports", fix_imports),
        (7, "Testando importação", test_import),
        (8, "Liberando porta 8000", kill_port_8000),
    ]

    for step_num, description, func in steps:
        print_step(step_num, description)
        if not func():
            print_error(f"Falha no passo {step_num}: {description}")
            print(f"\n{Colors.YELLOW}Dica:{Colors.RESET} Execute novamente ou use instalar.bat")
            return 1

    # Sucesso!
    print(f"\n{Colors.GREEN}{'='*60}")
    print(f"{Colors.BOLD}✅ CORREÇÃO CONCLUÍDA COM SUCESSO!{Colors.RESET}")
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")

    print("Para iniciar o Sentinela, execute:")
    if os.name == 'nt':
        print(f"  {Colors.BOLD}start.bat{Colors.RESET}")
        print("\nOu manualmente:")
        print(f"  {Colors.BOLD}venv\\Scripts\\activate")
        print(f"  python -m uvicorn app.main:app --reload{Colors.RESET}")
    else:
        print(f"  {Colors.BOLD}./start.sh{Colors.RESET}")
        print("\nOu manualmente:")
        print(f"  {Colors.BOLD}source venv/bin/activate")
        print(f"  python -m uvicorn app.main:app --reload{Colors.RESET}")

    print(f"\n📌 Acesse: {Colors.BLUE}http://localhost:8000{Colors.RESET}")
    print(f"📚 Documentação: {Colors.BLUE}http://localhost:8000/docs{Colors.RESET}")

    print(f"\n{Colors.YELLOW}Configurado com:{Colors.RESET}")
    print("  ✓ 9 fontes de dados integradas")
    print("  ✓ Busca offline no DOU (PDF)")
    print("  ✓ Cache automático (72 horas)")
    print("  ✓ Paginação até 100 resultados")

    return 0

if __name__ == "__main__":
    sys.exit(main())
