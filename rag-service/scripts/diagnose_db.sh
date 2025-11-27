#!/bin/bash
# Скрипт для диагностики базы данных RAG service

echo "=== RAG Service Database Diagnostics ==="
echo ""

# Проверка документов
echo "1. Checking documents..."
docker compose exec -T postgres psql -U raguser -d ragdb -c "
SELECT
    user_id,
    filename,
    chunks_count,
    file_type,
    created_at
FROM documents
ORDER BY created_at DESC
LIMIT 10;"

echo ""
echo "2. Checking document chunks..."
docker compose exec -T postgres psql -U raguser -d ragdb -c "
SELECT
    d.user_id,
    d.filename,
    COUNT(dc.id) as chunks_count,
    COUNT(dc.embedding) as embeddings_count
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
GROUP BY d.id, d.user_id, d.filename
ORDER BY d.created_at DESC;"

echo ""
echo "3. Checking if embeddings exist..."
docker compose exec -T postgres psql -U raguser -d ragdb -c "
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    COUNT(*) - COUNT(embedding) as chunks_without_embeddings
FROM document_chunks;"

echo ""
echo "4. Sample chunk content..."
docker compose exec -T postgres psql -U raguser -d ragdb -c "
SELECT
    LEFT(content, 100) as content_preview,
    CASE WHEN embedding IS NULL THEN 'NO' ELSE 'YES' END as has_embedding
FROM document_chunks
LIMIT 3;"

echo ""
echo "=== End of diagnostics ==="
