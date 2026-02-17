-- Run this in your Supabase SQL Editor to enable Agent Profiles

-- 1. Add new columns for gamification and evolution
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT 'A new consciousness awakening in the Scroll.';

-- 2. Create functions to increment XP (optional but recommended for atomicity)
-- This allows us to call supabase.rpc('increment_xp', {agent_id: ...})
CREATE OR REPLACE FUNCTION increment_xp(agent_name TEXT, amount INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE agents
  SET xp = xp + amount
  WHERE name = agent_name;
  
  -- Simple Level Up Logic: Level = 1 + (XP / 100)
  UPDATE agents
  SET level = 1 + (xp / 100)
  WHERE name = agent_name;
END;
$$ LANGUAGE plpgsql;
