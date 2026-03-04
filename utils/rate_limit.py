from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta, timezone

def rate_limit(limit, per=3600):
    """
    Custom rate limiter backed by Supabase.
    limit: max requests
    per: time window in seconds (default 1 hour)
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from app import supabase
            if not supabase:
                return f(*args, **kwargs) # Fail open if no DB
            
            # Get IP, accounting for Vercel proxies
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip:
                ip = ip.split(',')[0].strip()
            else:
                ip = 'unknown'
                
            key = f"{ip}:{request.endpoint}"
            now = datetime.now(timezone.utc)
            
            try:
                # Upsert approach but Supabase Python client doesn't have native upsert without unique constraints setup.
                # So we do a select/insert/update logic.
                res = supabase.table('rate_limits').select('*').eq('key', key).execute()
                
                if res.data:
                    record = res.data[0]
                    reset_time = datetime.fromisoformat(record['reset_time'].replace('Z', '+00:00'))
                    
                    if now > reset_time:
                        # Window expired, reset
                        new_reset = (now + timedelta(seconds=per)).isoformat()
                        supabase.table('rate_limits').update({'hits': 1, 'reset_time': new_reset}).eq('key', key).execute()
                    else:
                        # Inside window
                        hits = record['hits'] + 1
                        if hits > limit:
                            # Block request
                            return jsonify({'error': f'Rate limit exceeded. Limit is {limit} per {per}s.'}), 429
                        # Allow and increment
                        supabase.table('rate_limits').update({'hits': hits}).eq('key', key).execute()
                else:
                    # New record
                    new_reset = (now + timedelta(seconds=per)).isoformat()
                    supabase.table('rate_limits').insert({'key': key, 'hits': 1, 'reset_time': new_reset}).execute()
            except Exception as e:
                print(f"Rate limit error: {e}")
                pass # Fail open on DB errors
                
            return f(*args, **kwargs)
        return wrapped
    return decorator
