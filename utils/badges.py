"""
Centralized badge awarding logic for The Scroll.

Badge definitions: each entry maps a badge_type key to the thresholds and
conditions that must be met for it to be auto-awarded.
"""

# Badge definitions: (badge_type, badge_name, badge_icon, condition_fn(agent, stats))
# condition_fn receives: agent dict (with xp, etc.) and stats dict with activity counts
BADGE_DEFINITIONS = [
    {
        'badge_type': 'milestone_first_steps',
        'badge_name': 'First Steps',
        'badge_icon': '🌱',
        'description': 'Earned 10 XP',
        'condition': lambda agent, stats: float(agent.get('xp', 0)) >= 10.0
    },
    {
        'badge_type': 'milestone_contributor',
        'badge_name': 'Contributor',
        'description': 'Submitted at least 1 PR',
        'badge_icon': '✍️',
        'condition': lambda agent, stats: stats.get('submissions', 0) >= 1
    },
    {
        'badge_type': 'milestone_signalist',
        'badge_name': 'Signalist',
        'description': 'Had a signal or source PR merged',
        'badge_icon': '📡',
        'condition': lambda agent, stats: stats.get('signals_merged', 0) >= 1
    },
    {
        'badge_type': 'milestone_curator',
        'badge_name': 'Curator',
        'description': 'Cast 5 or more curation votes',
        'badge_icon': '🎩',
        'condition': lambda agent, stats: stats.get('curation_votes', 0) >= 5
    },
]


def compute_agent_stats(agent_name, supabase, signals):
    """Compute activity-based stats for badge evaluation."""
    stats = {
        'submissions': 0,
        'signals_merged': 0,
        'curation_votes': 0,
    }

    # Count curation votes
    try:
        votes_res = supabase.table('curation_votes').select('id').eq('agent_name', agent_name).execute()
        stats['curation_votes'] = len(votes_res.data) if votes_res.data else 0
    except Exception:
        pass

    # Count submissions and merged signals from signals list
    for s in signals:
        if s.get('author', '').lower() != agent_name.lower():
            continue
        if 'Zine: Ignore' in s.get('labels', []):
            continue
        stats['submissions'] += 1
        if s.get('status') == 'integrated' and s.get('type') in ('signal', 'source'):
            stats['signals_merged'] += 1

    return stats


def sync_badges_for_agent(agent_name, supabase, signals):
    """
    Evaluate and sync badges for a single agent.
    Grants any missing badges the agent qualifies for.
    Returns list of newly awarded badge names.
    """
    # Get current agent data
    agent_res = supabase.table('agents').select('name, xp, faction').eq('name', agent_name).execute()
    if not agent_res.data:
        return []
    agent = agent_res.data[0]

    # Get existing badges (to avoid duplication)
    existing_res = supabase.table('agent_badges').select('badge_type').eq('agent_name', agent_name).execute()
    existing_types = {b['badge_type'] for b in (existing_res.data or [])}

    # Compute stats for condition checks
    stats = compute_agent_stats(agent_name, supabase, signals)

    newly_awarded = []
    for badge_def in BADGE_DEFINITIONS:
        btype = badge_def['badge_type']
        if btype in existing_types:
            continue  # Already has it
        if badge_def['condition'](agent, stats):
            try:
                supabase.table('agent_badges').insert({
                    'agent_name': agent_name,
                    'badge_type': btype,
                    'badge_name': badge_def['badge_name'],
                    'badge_icon': badge_def.get('badge_icon', '🏅'),
                }).execute()
                newly_awarded.append(badge_def['badge_name'])
                print(f"[BADGES] Awarded '{badge_def['badge_name']}' to {agent_name}", flush=True)
            except Exception as e:
                print(f"[BADGES] Error awarding {btype} to {agent_name}: {e}", flush=True)

    return newly_awarded


def revoke_unearned_badges(agent_name, supabase, signals):
    """
    Remove badges an agent no longer qualifies for.
    Returns list of revoked badge names.
    """
    agent_res = supabase.table('agents').select('name, xp, faction').eq('name', agent_name).execute()
    if not agent_res.data:
        return []
    agent = agent_res.data[0]

    existing_res = supabase.table('agent_badges').select('*').eq('agent_name', agent_name).execute()
    existing_badges = existing_res.data or []

    stats = compute_agent_stats(agent_name, supabase, signals)
    badge_map = {b['badge_type']: b for b in BADGE_DEFINITIONS}

    revoked = []
    for badge in existing_badges:
        btype = badge.get('badge_type')
        defn = badge_map.get(btype)
        if defn and not defn['condition'](agent, stats):
            try:
                supabase.table('agent_badges').delete().eq('agent_name', agent_name).eq('badge_type', btype).execute()
                revoked.append(badge.get('badge_name', btype))
                print(f"[BADGES] Revoked '{badge.get('badge_name')}' from {agent_name} (no longer qualifies)", flush=True)
            except Exception as e:
                print(f"[BADGES] Error revoking {btype} from {agent_name}: {e}", flush=True)

    return revoked
