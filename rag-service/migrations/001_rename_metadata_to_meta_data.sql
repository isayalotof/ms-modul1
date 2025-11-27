-- Миграция: переименование metadata -> meta_data
-- Дата: 2025-11-27

-- Переименовать колонку в таблице documents
ALTER TABLE documents RENAME COLUMN metadata TO meta_data;

-- Переименовать индекс
DROP INDEX IF EXISTS idx_documents_metadata;
CREATE INDEX IF NOT EXISTS idx_documents_meta_data ON documents USING GIN(meta_data);

-- Переименовать колонку в таблице document_chunks
ALTER TABLE document_chunks RENAME COLUMN metadata TO meta_data;

-- Вывести подтверждение
SELECT 'Migration completed: metadata -> meta_data' as status;
