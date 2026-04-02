-- Create separate databases for each service on shared Postgres instance
CREATE DATABASE langfuse;
CREATE DATABASE temporal;
CREATE DATABASE temporal_visibility;

-- Enable pgvector extension on the default database (used by R2R)
CREATE EXTENSION IF NOT EXISTS vector;
