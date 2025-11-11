# Sentinela - Interface Web

Interface web moderna e intuitiva para o sistema Sentinela de busca unificada em diários oficiais brasileiros.

## 🎨 Características

- **Design Moderno**: Interface limpa com animações suaves
- **Responsivo**: Funciona em desktop, tablet e mobile
- **Tema Dark/Light**: Alternância de tema com persistência
- **Busca em Tempo Real**: Resultados instantâneos
- **Filtros Avançados**: Datas, UFs, fontes, ordenação
- **Paginação**: Navegação eficiente entre resultados
- **Zero Dependências**: HTML5, CSS3, JavaScript vanilla

## 🏗️ Estrutura

```
frontend/
├── index.html          # Página principal
├── css/
│   └── styles.css     # Estilos modernos
├── js/
│   └── app.js         # Lógica da aplicação
└── assets/            # Imagens e recursos
```

## 🚀 Como Usar

### Método 1: Com o Backend (Recomendado)

Execute o backend FastAPI e acesse http://localhost:8000

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

### Método 2: Desenvolvimento Separado

Para desenvolvimento do frontend, use um servidor HTTP simples:

```bash
# Python
cd frontend
python -m http.server 8080

# Node.js
npx http-server frontend -p 8080

# PHP
php -S localhost:8080 -t frontend
```

Depois configure a API_BASE_URL em `js/app.js` se necessário.

## 🎯 Funcionalidades

### Busca Básica

1. Digite o termo na barra de busca
2. Clique em "Buscar" ou pressione Enter
3. Veja resultados de todas as fontes

### Filtros Avançados

- **Datas**: Filtrar por período de publicação
- **Estados**: Selecionar múltiplas UFs (Ctrl+Click)
- **Fontes**: Escolher quais fontes consultar
- **Ordenação**: Por relevância ou data
- **Tamanho**: Resultados por página (10-100)

### Navegação

- **Buscar**: Página principal de busca
- **Fontes**: Ver status de todas as fontes
- **Sobre**: Informações do projeto

### Temas

Clique no botão 🌓 para alternar entre tema claro e escuro.

## 🎨 Customização

### Cores

Edite as variáveis CSS em `css/styles.css`:

```css
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    /* ... */
}
```

### Logo

Substitua o emoji 🔍 por uma imagem:

```html
<!-- Antes -->
<span class="logo-icon">🔍</span>

<!-- Depois -->
<img src="/assets/logo.png" alt="Sentinela" class="logo-icon">
```

### API URL

Para apontar para outra API, edite `js/app.js`:

```javascript
const API_BASE_URL = 'https://sua-api.com';
```

## 📱 Responsividade

A interface se adapta automaticamente para:

- **Desktop** (1200px+): Layout completo
- **Tablet** (768px-1199px): Layout adaptado
- **Mobile** (<768px): Layout otimizado para toque

## 🔧 Tecnologias

- **HTML5**: Semântico e acessível
- **CSS3**: Grid, Flexbox, animações, variáveis
- **JavaScript ES6+**: Async/await, fetch, modules
- **Font**: System fonts (sans-serif nativo)

## ⚡ Performance

- Zero dependências externas
- CSS e JS minificáveis
- Lazy loading de imagens (se houver)
- Cache de tema no localStorage

## 🌐 Navegadores Suportados

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Opera 76+

## 🐛 Debug

Console do navegador mostra logs úteis:

```javascript
// Ativar modo debug
localStorage.setItem('debug', 'true');

// Ver logs detalhados
console.log('Search filters:', filters);
```

## 📖 API Endpoints Usados

- `GET /api/v1/search` - Busca unificada
- `GET /api/v1/sources` - Listar fontes
- `GET /api/v1/health` - Health check

## 🎓 Boas Práticas Implementadas

- ✅ Código semântico
- ✅ Acessibilidade (ARIA labels)
- ✅ Segurança (escapeHtml, CORS)
- ✅ Performance (debouncing, lazy loading)
- ✅ UX (loading states, error handling)
- ✅ Mobile-first design

## 🔮 Próximas Melhorias

- [ ] PWA (Progressive Web App)
- [ ] Busca por voz
- [ ] Exportar resultados (CSV, PDF)
- [ ] Compartilhar buscas (link)
- [ ] Histórico de buscas
- [ ] Favoritos
- [ ] Notificações push
- [ ] Modo offline

## 📝 Licença

MIT License - Veja [LICENSE](../LICENSE)

---

**Desenvolvido com 💚 para facilitar acesso à informação pública brasileira**
