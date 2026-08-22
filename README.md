LexIA — Intelligent Legal Document Analysis

LexIA is a full-stack application designed to process, search, and extract structured information from legal documents.

The system supports document ingestion from TXT, Markdown, and PDF files while preserving the structure of legal articles. It provides a hybrid search engine combining BM25 lexical search and vector similarity, using Reciprocal Rank Fusion (RRF) to improve the retrieval of relevant content.

LexIA also includes a structured information extraction pipeline capable of identifying elements such as obligations, deadlines, penalties, and references. The extraction system can operate entirely offline using deterministic rules or optionally integrate with an LLM.

A key feature of the project is its focus on measurable evaluation. LexIA includes a golden dataset and evaluation pipeline using metrics such as Macro-F1, Micro-F1, Recall@K, and MRR to measure extraction and retrieval quality.

Key Features
Legal document ingestion from TXT, Markdown, and PDF
Article-aware document chunking
Hybrid lexical and vector search
BM25 and TF-IDF retrieval
Reciprocal Rank Fusion (RRF)
Structured information extraction
Pydantic-based data validation
Optional LLM integration
Offline-first architecture
Automatic JSON validation and recovery
Rule-based extraction fallback
Golden Set evaluation
Automated backend and frontend tests
Tech Stack
Python
FastAPI
React
TypeScript
Vite
Pydantic
BM25
TF-IDF
NLP
LLM
Pytest
Vitest
Evaluation

The project includes automated evaluation to measure the quality of both information extraction and document retrieval.

Current evaluation results include:

Macro-F1: 0.972
Recall@5: 1.000
MRR: 0.903
Backend test coverage: 95%

These metrics provide an objective way to evaluate the effectiveness of the implemented pipelines.

Architecture

LexIA is divided into frontend and backend layers:

Frontend

React
TypeScript
Vite

Backend

Python
FastAPI
Pydantic
Search and extraction pipelines

AI / Information Retrieval

BM25
TF-IDF
Vector similarity
Reciprocal Rank Fusion
Optional LLM integration
Project Goals

The main goal of LexIA is to explore the application of software engineering, information retrieval, natural language processing, and artificial intelligence to the analysis of legal documents.

The project focuses not only on implementing features, but also on testing, validation, evaluation, and measurable system performance.
