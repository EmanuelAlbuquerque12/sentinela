# Guia de Instalação - Problemas Comuns no Windows

## ⚠️ Erro: "Falha ao instalar dependências"

Se você recebeu o erro relacionado a compilação (Rust/C), siga estas soluções:

---

## ✅ Solução 1: Usar Dependências Essenciais (Recomendado)

O arquivo `requirements.txt` foi atualizado para usar apenas dependências pré-compiladas.

**Execute novamente:**
```bash
start.bat
```

Deve funcionar agora! ✅

---

## ✅ Solução 2: Instalação Manual Mínima

Se ainda houver problemas, instale manualmente o essencial:

```bash
# 1. Ativar ambiente virtual
venv\Scripts\activate

# 2. Instalar dependências uma por uma
pip install fastapi==0.109.0
pip install uvicorn[standard]==0.27.0
pip install httpx==0.26.0
pip install pydantic==2.5.3
pip install pydantic-settings==2.1.0
pip install python-dotenv==1.0.0

# 3. Executar servidor
python -m uvicorn app.main:app --reload
```

---

## ✅ Solução 3: Usar Wheels Pré-compilados

Para bibliotecas que requerem compilação (opcional):

1. **Acesse:** https://www.lfd.uci.edu/~gohlke/pythonlibs/
2. **Baixe** os arquivos `.whl` para:
   - `cryptography`
   - `lxml`
   - `Scrapy`
3. **Instale:**
   ```bash
   pip install nome_do_arquivo.whl
   ```

---

## ✅ Solução 4: Instalar Build Tools (Avançado)

Se quiser todas as funcionalidades:

### Opção A: Visual Studio Build Tools

1. **Baixe:** https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. **Instale** "Desktop development with C++"
3. **Reinicie** o computador
4. **Execute** `start.bat` novamente

### Opção B: Rust (para cryptography, orjson)

1. **Baixe:** https://rustup.rs/
2. **Instale** Rust
3. **Reinicie** o terminal
4. **Execute:**
   ```bash
   pip install -r requirements-full.txt
   ```

---

## 🎯 Qual Versão Usar?

### requirements.txt (Essencial) ✅
**Use se:**
- Quer apenas usar o Sentinela
- Não quer instalar ferramentas de build
- Windows sem Visual Studio

**Inclui:**
- FastAPI, Uvicorn (servidor)
- httpx (requisições HTTP)
- Pydantic (validação)
- Python-dotenv (config)

**Funciona:** ✅ Busca em todas as fontes

---

### requirements-full.txt (Completo) 🔧
**Use se:**
- Quer recursos extras (cache Redis, logging avançado)
- Quer desenvolver o projeto
- Tem ferramentas de build instaladas

**Inclui:**
- Tudo do essencial +
- Redis (cache)
- BeautifulSoup (scraping)
- Pytest (testes)
- Black, Ruff (formatação)

---

## 🐛 Outros Problemas Comuns

### Problema: "Python não encontrado"

**Solução:**
1. Instale Python 3.10+ em https://www.python.org/downloads/
2. ⚠️ **Importante:** Marque "Add Python to PATH" durante instalação
3. Reinicie o terminal

---

### Problema: "Porta 8000 em uso"

**Solução:**
```bash
# Descobrir processo na porta 8000
netstat -ano | findstr :8000

# Encerrar processo (use o PID da coluna da direita)
taskkill /F /PID <numero_do_pid>
```

Ou o script `start.bat` faz isso automaticamente agora! ✅

---

### Problema: "Permissão negada"

**Solução:**
1. Execute o terminal como **Administrador**
2. Ou mude a pasta de instalação para um local sem restrições

---

### Problema: "Módulo não encontrado"

**Solução:**
```bash
# Verificar se está no ambiente virtual
venv\Scripts\activate

# Ver pacotes instalados
pip list

# Reinstalar
pip install -r requirements.txt --force-reinstall
```

---

## ✅ Verificar Instalação

Execute este comando para testar:

```bash
python -c "import fastapi, uvicorn, httpx, pydantic; print('✅ Tudo instalado corretamente!')"
```

Se aparecer "✅ Tudo instalado corretamente!", está pronto!

---

## 📞 Ainda com Problemas?

1. **Abra uma issue:** https://github.com/EmanuelAlbuquerque12/sentinela/issues
2. **Inclua:**
   - Versão do Python (`python --version`)
   - Sistema operacional
   - Mensagem de erro completa
   - O que já tentou

---

## 🎯 TL;DR (Resumo Rápido)

```bash
# 1. Certifique-se que Python 3.10+ está instalado
python --version

# 2. Execute
start.bat

# 3. Se der erro de compilação, já está corrigido!
#    O requirements.txt foi atualizado para usar apenas
#    pacotes pré-compilados

# 4. Acesse
#    http://localhost:8000
```

---

**💡 Dica:** Use `requirements.txt` (essencial) para começar rápido. Depois, se precisar, instale `requirements-full.txt` com as ferramentas de build.
