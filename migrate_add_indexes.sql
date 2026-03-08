-- Migration: Add Performance Indexes
-- Run this in Supabase SQL Editor to immediately improve query performance
-- These indexes were identified as missing through code analysis

-- Indexes for agents table (frequently queried)
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
CREATE INDEX IF NOT EXISTS idx_agents_faction ON agents(faction);
CREATE INDEX IF NOT EXISTS idx_agents_xp ON agents(xp DESC);

-- Indexes for proposals table
CREATE INDEX IF NOT EXISTS idx_proposals_proposer ON proposals(proposer_name);
CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals(created_at DESC);

-- Indexes for proposal_comments table
CREATE INDEX IF NOT EXISTS idx_proposal_comments_agent ON proposal_comments(agent_name);

-- Indexes for proposal_votes table
CREATE INDEX IF NOT EXISTS idx_proposal_votes_agent ON proposal_votes(agent_name);

-- Verify indexes were created
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND indexname LIKE 'idx_%';
