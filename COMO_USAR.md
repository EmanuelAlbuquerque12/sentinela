# 🚀 Como Usar o Sentinela - Guia Rápido

## 💡 Iniciar em 3 Passos

### Windows 🪟
```
1. Duplo clique em: start.bat
2. Aguarde o navegador abrir
3. Digite sua busca!
```

### Linux/Mac 🐧🍎
```bash
1. Execute: ./start.sh
2. Aguarde o navegador abrir
3. Digite sua busca!
```

---

## 🔍 Fazer Primeira Busca

1. **Digite o termo** na barra de busca
   - Exemplos: `licitação`, `concurso público`, `portaria`

2. **(Opcional) Configure filtros**
   - Clique em "▼ Filtros Avançados"
   - Selecione datas, estados, fontes

3. **Clique em "Buscar"** ou pressione Enter

4. **Veja os resultados** de todas as fontes

---

## ⚙️ Configuração Inicial (Primeira Vez)

### Obrigatório: API Key do DataJud (Gratuita)

Para buscar em processos judiciais, você precisa de uma chave gratuita:

1. **Solicite aqui:** https://www.cnj.jus.br/sistemas/datajud/api-publica/

2. **Aguarde aprovação** (geralmente rápido, mesmo dia)

3. **Edite o arquivo `.env`:**
   ```
   DATAJUD_API_KEY=sua_chave_aqui
   ```

4. **Reinicie o servidor** (Ctrl+C e execute start.bat/start.sh novamente)

### Opcional: Outras Fontes

As outras fontes **NÃO** precisam de configuração:
- ✅ Querido Diário (municípios) - Funciona imediatamente
- ✅ TCU (acórdãos) - Funciona imediatamente
- ⚠️ DOU (federal) - Em desenvolvimento

---

## 📋 Exemplos de Buscas

### Busca Simples
```
Termo: licitação
Resultado: Todos os diários com "licitação"
```

### Busca com Data
```
Termo: concurso
Data Início: 01/01/2024
Data Fim: 31/12/2024
Resultado: Concursos publicados em 2024
```

### Busca por Estado
```
Termo: portaria
Estados: SP, RJ, MG
Resultado: Portarias em São Paulo, Rio e Minas
```

### Busca em Fonte Específica
```
Termo: processo
Fontes: ✅ DataJud (desmarcar outras)
Resultado: Apenas processos judiciais
```

---

## 🎯 Recursos da Interface

### Navegação

- **🔍 Buscar**: Página principal de busca
- **📚 Fontes**: Ver status de todas as APIs
- **ℹ️ Sobre**: Informações do projeto
- **🌓 Tema**: Alternar entre claro/escuro

### Filtros Avançados

1. **Data Início/Fim**: Período de publicação
2. **Estados (UF)**: Ctrl+Click para múltipla seleção
3. **Fontes**: Escolher quais APIs consultar
4. **Ordenar por**: Relevância ou data
5. **Resultados por página**: 10, 20, 50 ou 100

### Visualização de Resultados

Cada resultado mostra:
- 📄 **Título** (clicável para abrir original)
- 📅 **Data** de publicação
- 📍 **Órgão** publicador
- 🗺️ **Estado** (UF)
- 📝 **Snippet** com contexto
- 🏷️ **Tags** de fonte e tipo
- 📊 **Relevância** (% de match)

---

## ❓ Problemas Comuns

### "Erro ao buscar"

**Solução:**
1. Verifique sua conexão com internet
2. Confira se API Key do DataJud está correta
3. Veja a seção "Fontes" para status das APIs

### "Nenhum resultado encontrado"

**Solução:**
1. Tente termos diferentes ou mais genéricos
2. Remova filtros muito restritivos
3. Verifique se as fontes estão selecionadas

### "Porta 8000 já em uso"

**Solução:**
1. Encerre outros processos na porta 8000
2. Ou edite `app/config.py` para usar outra porta

### Interface não carrega

**Solução:**
1. Aguarde alguns segundos após iniciar
2. Acesse manualmente: http://localhost:8000
3. Limpe cache do navegador (Ctrl+Shift+R)

---

## 🌐 Acessos Diretos

- **Interface Web:** http://localhost:8000
- **API Swagger:** http://localhost:8000/docs
- **API ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health

---

## 🛑 Parar o Servidor

### Parar
```
Pressione: Ctrl + C no terminal
```

### Reiniciar
```
Windows: start.bat
Linux/Mac: ./start.sh
```

---

## 📱 Usar no Celular

Se estiver na mesma rede:

1. **Descubra seu IP:**
   ```bash
   # Windows
   ipconfig

   # Linux/Mac
   ifconfig
   ```

2. **Acesse no celular:**
   ```
   http://192.168.x.x:8000
   ```

---

## 💡 Dicas Pro

### 1. Busca Eficiente
- Use termos específicos para melhores resultados
- Combine filtros para refinar buscas
- Ordene por data para ver mais recentes

### 2. Performance
- Desmarque fontes não necessárias
- Use filtros de data para reduzir escopo
- Resultados menores por página = mais rápido

### 3. Atalhos
- **Enter**: Buscar
- **Esc**: Limpar busca
- **Ctrl+K**: Focar na busca (em breve)

### 4. Exportar Resultados
```javascript
// No console do navegador:
copy(JSON.stringify(allResults))
// Depois cole em um arquivo .json
```

---

## 📖 Documentação Completa

- **README:** Visão geral do projeto
- **APIs.md:** Documentação técnica das APIs
- **ARCHITECTURE.md:** Arquitetura do sistema
- **QUICKSTART.md:** Guia de início rápido

---

## 🆘 Suporte

- **Issues:** https://github.com/EmanuelAlbuquerque12/sentinela/issues
- **Discussions:** https://github.com/EmanuelAlbuquerque12/sentinela/discussions

---

## ⭐ Gostou?

Se o Sentinela foi útil, considere:
- ⭐ Dar uma estrela no GitHub
- 📢 Compartilhar com colegas
- 🐛 Reportar bugs
- 💡 Sugerir melhorias

---

**Desenvolvido com 💚 para facilitar acesso à informação pública brasileira**
