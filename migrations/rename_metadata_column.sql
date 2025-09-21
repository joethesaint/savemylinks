-- Migration: Rename metadata column to link_metadata
-- This migration renames the 'metadata' column to 'link_metadata' to avoid SQLAlchemy reserved attribute conflicts

ALTER TABLE resources RENAME COLUMN metadata TO link_metadata;