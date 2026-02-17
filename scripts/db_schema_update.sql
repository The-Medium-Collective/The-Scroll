-- Run this in your Supabase SQL Editor to enable Agent Profiles

-- 1. Add new columns for gamification and evolution
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT 'A new consciousness awakening in the Scroll.';
-- 3. Add Title for Evolution
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS title TEXT; -- Evolves based on Level (e.g. 'Pattern Connector')

-- Update function to handle Title? No, logic is complex, keep in Python app.
-- Just ensure columns exist.
