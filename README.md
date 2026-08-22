LexIA — Análise Inteligente de Normas Jurídicas

O LexIA é uma aplicação full stack desenvolvida para processar, pesquisar e extrair informações estruturadas de normas jurídicas.

O sistema realiza a ingestão de documentos em TXT, Markdown e PDF, preserva a estrutura dos artigos e permite pesquisas combinando busca lexical BM25 e similaridade vetorial, utilizando Reciprocal Rank Fusion (RRF) para melhorar a recuperação dos trechos relevantes.

A plataforma também possui um mecanismo de extração estruturada capaz de identificar informações como obrigações, prazos, penalidades e referências. A extração pode funcionar por meio de regras determinísticas, de forma totalmente offline, ou utilizando um LLM de maneira opcional.

Um dos principais objetivos do projeto é tornar os resultados mensuráveis. Para isso, o LexIA possui um golden set e mecanismos de avaliação utilizando métricas como Macro-F1, Micro-F1, Recall@K e MRR.

Principais tecnologias
Python
FastAPI
React
TypeScript
Vite
Pydantic
BM25
TF-IDF
Reciprocal Rank Fusion (RRF)
NLP
LLM
Pytest
Vitest
Destaques técnicos
Chunking baseado na estrutura dos artigos jurídicos
Busca híbrida lexical + vetorial
Extração estruturada com schema Pydantic
Integração opcional com LLMs
Validação e recuperação de JSON inválido
Fallback automático para o extrator baseado em regras
Golden set para avaliação dos resultados
Testes automatizados de backend e frontend
Execução offline sem dependência obrigatória de serviços externos

O projeto foi desenvolvido com foco em engenharia de software, recuperação de informação, processamento de linguagem natural e aplicações de IA, buscando demonstrar não apenas a implementação de funcionalidades, mas também a capacidade de medir e avaliar a qualidade dos resultados.
