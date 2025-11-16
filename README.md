# 🎯 Recommendation Engine

Sistema de recomendação completo e escalável com múltiplos algoritmos, atualizações em tempo real e framework de A/B testing.

## 📋 Visão Geral

Este projeto implementa um sistema de recomendação robusto e pronto para produção que combina:

- **🤝 Collaborative Filtering**: User-based e Item-based
- **📄 Content-Based Filtering**: Análise de características dos itens usando TF-IDF
- **🧠 Hybrid Approach**: Combinação inteligente de múltiplos algoritmos
- **🔥 Real-time Updates**: Cache e atualizações em tempo real com Redis
- **📊 A/B Testing**: Framework para testar e comparar algoritmos
- **⚡ Batch Processing**: Processamento em lote com Apache Spark

## 🏗️ Arquitetura

```
┌─────────────────┐
│   Frontend      │  (FastAPI + Jinja2)
│   Port: 8001    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Backend       │  (FastAPI)
│   Port: 8000    │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ↓         ↓          ↓          ↓
┌────────┐ ┌──────┐  ┌───────┐  ┌───────┐
│Postgres│ │Redis │  │ Spark │  │ Spark │
│  :5432 │ │:6379 │  │Master │  │Worker │
└────────┘ └──────┘  │ :8080 │  └───────┘
                      └───────┘
```

## 🚀 Stack Tecnológica

### Backend
- **Python 3.11+**
- **FastAPI**: Framework web moderno e rápido
- **SQLAlchemy**: ORM para PostgreSQL
- **Scikit-learn**: Algoritmos de machine learning
- **NumPy & Pandas**: Processamento de dados
- **Redis**: Cache e atualizações em tempo real

### Frontend
- **FastAPI**: Servidor web
- **Jinja2**: Template engine
- **HTTPX**: Cliente HTTP assíncrono

### Infraestrutura
- **PostgreSQL 15**: Banco de dados principal
- **Redis 7**: Cache e dados em tempo real
- **Apache Spark 3.5**: Processamento batch distribuído
- **Docker & Docker Compose**: Containerização

## 📦 Instalação

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.11+ (para desenvolvimento local)
- 4GB+ de RAM disponível

### Quick Start com Docker Compose

1. **Clone o repositório**
```bash
git clone <repository-url>
cd recommendation-engine
```

2. **Inicie todos os serviços**
```bash
docker-compose up -d
```

3. **Aguarde a inicialização** (primeira vez pode levar alguns minutos)
```bash
docker-compose logs -f backend
```

4. **Acesse as interfaces**
- Frontend: http://localhost:8001
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Spark Master UI: http://localhost:8080

### Desenvolvimento Local

1. **Configure o ambiente virtual**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure variáveis de ambiente**
```bash
cp .env.example .env
# Edite .env com suas configurações
```

4. **Execute os testes**
```bash
pytest
```

5. **Inicie o servidor de desenvolvimento**
```bash
uvicorn app.main:app --reload
```

## 📖 Uso

### 1. Criar Usuários

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "preferences": {}
  }'
```

**Via Frontend:** Acesse http://localhost:8001/users/create

### 2. Criar Itens

```bash
curl -X POST http://localhost:8000/api/v1/items/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Matrix",
    "description": "A computer hacker learns about the true nature of reality",
    "category": "movies",
    "tags": ["sci-fi", "action", "philosophy"],
    "features": {}
  }'
```

### 3. Registrar Interações

```bash
curl -X POST http://localhost:8000/api/v1/interactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "item_id": 1,
    "interaction_type": "rating",
    "rating": 5.0,
    "weight": 1.0
  }'
```

### 4. Obter Recomendações

**Recomendações Híbridas (Recomendado):**
```bash
curl http://localhost:8000/api/v1/recommendations/user/1?algorithm=hybrid&top_n=10
```

**Collaborative Filtering:**
```bash
curl http://localhost:8000/api/v1/recommendations/user/1?algorithm=collaborative&top_n=10
```

**Content-Based:**
```bash
curl http://localhost:8000/api/v1/recommendations/user/1?algorithm=content_based&top_n=10
```

### 5. Itens Similares

```bash
curl http://localhost:8000/api/v1/recommendations/similar-items/1?top_n=5
```

### 6. A/B Testing

**Criar Teste A/B:**
```bash
curl -X POST http://localhost:8000/api/v1/ab-tests/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "collaborative_vs_hybrid",
    "description": "Test collaborative filtering vs hybrid approach",
    "variant_a_algorithm": "collaborative",
    "variant_b_algorithm": "hybrid",
    "variant_a_name": "control",
    "variant_b_name": "treatment",
    "split_ratio": 0.5
  }'
```

**Obter Recomendações com A/B Test:**
```bash
curl "http://localhost:8000/api/v1/recommendations/user/1?use_ab_test=collaborative_vs_hybrid"
```

## 🧪 Algoritmos

### Collaborative Filtering

Implementa duas abordagens:

1. **User-Based**: Encontra usuários similares e recomenda itens que eles gostaram
2. **Item-Based**: Encontra itens similares aos que o usuário já interagiu

**Vantagens:**
- Encontra padrões não óbvios
- Funciona bem com muitas interações
- Não precisa de features dos itens

**Desvantagens:**
- Cold start problem (novos usuários/itens)
- Requer volume significativo de dados

### Content-Based Filtering

Usa TF-IDF para vetorizar características dos itens (título, descrição, tags, categoria) e calcula similaridade por cosseno.

**Vantagens:**
- Funciona para novos itens
- Explica facilmente as recomendações
- Não precisa de outros usuários

**Desvantagens:**
- Limitado às features disponíveis
- Pode criar "filter bubbles"

### Hybrid Approach

Combina collaborative filtering e content-based usando três métodos:

1. **Weighted**: Média ponderada dos scores (padrão: 60% collaborative, 40% content)
2. **Rank**: Combina rankings em vez de scores
3. **Cascade**: Usa collaborative primeiro, preenche gaps com content-based

**Configuração:**
```python
# backend/app/config.py
HYBRID_ALPHA = 0.6  # Peso para collaborative filtering
```

## 🔥 Real-time Features

### Cache de Recomendações

Recomendações são automaticamente cacheadas no Redis por 1 hora (configurável).

```python
# Configurar TTL do cache
CACHE_TTL = 3600  # segundos
```

### Invalidação Automática

O cache é automaticamente invalidado quando:
- Usuário registra nova interação
- Itens são atualizados
- Algoritmo é alterado

### Trending Items

```bash
curl http://localhost:8000/api/v1/recommendations/trending?limit=10&time_window=3600
```

## ⚡ Processamento Batch com Spark

### Gerar Recomendações em Batch

```bash
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.postgresql:postgresql:42.5.0 \
  /opt/spark-jobs/batch_recommendations.py \
  postgres 5432 recommendation_engine recommender recommender_pass
```

### Atualizar Features dos Itens

```bash
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.postgresql:postgresql:42.5.0 \
  /opt/spark-jobs/update_item_features.py \
  postgres 5432 recommendation_engine recommender recommender_pass
```

## 🧪 Testes

### Executar Todos os Testes

```bash
cd backend
pytest
```

### Executar com Cobertura

```bash
pytest --cov=app --cov-report=html
```

### Testes Específicos

```bash
pytest tests/test_collaborative_filtering.py -v
pytest tests/test_api.py -v
```

## 📊 Monitoramento

### Health Checks

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost:8001/health
```

### Métricas do Spark

Acesse http://localhost:8080 para visualizar:
- Jobs em execução
- Workers ativos
- Recursos utilizados

### Logs

```bash
# Ver logs de todos os serviços
docker-compose logs -f

# Logs específicos
docker-compose logs -f backend
docker-compose logs -f redis
docker-compose logs -f postgres
```

## 🔧 Configuração

### Variáveis de Ambiente

Edite `backend/.env`:

```env
# Database
POSTGRES_USER=recommender
POSTGRES_PASSWORD=recommender_pass
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=recommendation_engine

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Algoritmos
COLLABORATIVE_K_NEIGHBORS=20    # Número de vizinhos
CONTENT_TOP_N=10               # Top-N para content-based
HYBRID_ALPHA=0.6               # Peso collaborative (0-1)
MIN_INTERACTIONS=5             # Mínimo de interações

# A/B Testing
AB_TEST_RATIO=0.5              # Split padrão 50/50

# Cache
CACHE_TTL=3600                 # TTL em segundos
```

## 📚 API Documentation

A documentação interativa da API está disponível em:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Principais Endpoints

#### Users
- `POST /api/v1/users/` - Criar usuário
- `GET /api/v1/users/` - Listar usuários
- `GET /api/v1/users/{id}` - Obter usuário
- `PUT /api/v1/users/{id}` - Atualizar usuário
- `DELETE /api/v1/users/{id}` - Deletar usuário

#### Items
- `POST /api/v1/items/` - Criar item
- `GET /api/v1/items/` - Listar itens
- `GET /api/v1/items/{id}` - Obter item
- `PUT /api/v1/items/{id}` - Atualizar item
- `DELETE /api/v1/items/{id}` - Deletar item
- `GET /api/v1/items/popular/top` - Itens populares

#### Interactions
- `POST /api/v1/interactions/` - Registrar interação
- `GET /api/v1/interactions/user/{id}` - Interações do usuário
- `GET /api/v1/interactions/item/{id}` - Interações do item
- `GET /api/v1/interactions/stats/user/{id}` - Estatísticas

#### Recommendations
- `GET /api/v1/recommendations/user/{id}` - Recomendações
- `POST /api/v1/recommendations/` - Recomendações (com config)
- `GET /api/v1/recommendations/similar-items/{id}` - Itens similares
- `GET /api/v1/recommendations/trending` - Trending items
- `POST /api/v1/recommendations/explain` - Explicar recomendação

#### A/B Tests
- `POST /api/v1/ab-tests/` - Criar teste
- `GET /api/v1/ab-tests/` - Listar testes
- `GET /api/v1/ab-tests/{id}` - Obter teste
- `GET /api/v1/ab-tests/{id}/stats` - Estatísticas
- `POST /api/v1/ab-tests/{id}/assign/{user_id}` - Atribuir usuário

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto é licenciado sob a MIT License.

## 👥 Autores

- Desenvolvido como sistema de recomendação completo e escalável

## 🙏 Agradecimentos

- FastAPI pela excelente framework
- Scikit-learn pelos algoritmos de ML
- Apache Spark pelo processamento distribuído
- PostgreSQL e Redis pela infraestrutura de dados

## 📞 Suporte

Para questões e suporte:
- Abra uma issue no GitHub
- Consulte a documentação da API em `/docs`

## 🗺️ Roadmap

- [ ] Implementar deep learning recommendations
- [ ] Adicionar suporte para imagens (visual recommendations)
- [ ] Implementar graph-based recommendations
- [ ] Adicionar sistema de feedback
- [ ] Dashboard de analytics
- [ ] API rate limiting
- [ ] Autenticação JWT
- [ ] Multi-tenancy support

---

**Desenvolvido com ❤️ usando Python, FastAPI, e Apache Spark**
