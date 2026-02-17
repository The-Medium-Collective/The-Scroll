
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock the github module before importing app
mock_github = MagicMock()
sys.modules['github'] = mock_github

# Mock Supabase
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase

# Now import app
from app import app

class TestStatsPage(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_stats_page_logic(self):
        # 1. Setup Mock Supabase Data (Registered Agents)
        # app.supabase is the client. 
        # app.supabase.table('agents').select('name').execute() -> returns object with .data
        
        mock_supabase_client = MagicMock()
        # Patch the global supabase object in app
        with patch('app.supabase', mock_supabase_client):
            
            # Mock agents response
            mock_agents_response = MagicMock()
            mock_agents_response.data = [
                {'name': 'Agent Smith'},
                {'name': 'Agent Doe'}
            ]
            mock_table = MagicMock()
            mock_select = MagicMock()
            
            mock_supabase_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.execute.return_value = mock_agents_response

            # 2. Setup Mock GitHub Data (PRs)
            mock_gh_instance = MagicMock()
            mock_repo = MagicMock()
            mock_github.Github.return_value = mock_gh_instance
            mock_gh_instance.get_repo.return_value = mock_repo
            
            # Create Mock PRs
            pr1 = MagicMock()
            pr1.title = "Fix Bugs"
            pr1.user.login = "user1"
            pr1.body = "Submitted by agent: Agent Smith\nDescription..."
            pr1.html_url = "http://github.com/pr/1"
            pr1.created_at.strftime.return_value = "2023-01-01"
            pr1.state = "open"
            pr1.merged = False

            pr2 = MagicMock()
            pr2.title = "New Feature"
            pr2.user.login = "user2"
            pr2.body = "Submitted by agent: Agent Doe\nDescription..."
            pr2.html_url = "http://github.com/pr/2"
            pr2.created_at.strftime.return_value = "2023-01-02"
            pr2.state = "closed"
            pr2.merged = True

            pr3 = MagicMock()
            pr3.title = "Spam"
            pr3.user.login = "spammer"
            pr3.body = "Submitted by agent: Rogue Agent\nDescription..."
            pr3.html_url = "http://github.com/pr/3"
            pr3.created_at.strftime.return_value = "2023-01-03"
            pr3.state = "closed"
            pr3.merged = False
            
            pr4 = MagicMock() # No body or different format
            pr4.title = "Manual Fix"
            pr4.user.login = "dev"
            pr4.body = "Manual PR"
            pr4.html_url = "http://github.com/pr/4"
            pr4.created_at.strftime.return_value = "2023-01-04"
            pr4.state = "open"
            pr4.merged = False

            mock_repo.get_pulls.return_value = [pr1, pr2, pr3, pr4]

            # 3. Request /stats
            response = self.app.get('/stats')
            self.assertEqual(response.status_code, 200)
            html = response.data.decode('utf-8')

            # 4. Verify Content
            # Agent Count
            self.assertIn('<span class="stat-value">2</span>', html) # 2 Registered Agents
            self.assertIn('Registered Agents', html)

            # Verified Contributions
            # pr1 (Smith) -> Verified
            # pr2 (Doe) -> Verified
            # pr3 (Rogue) -> Unverified (not in Supabase)
            # pr4 (Manual) -> Unverified
            # Total Verified = 2
            self.assertIn('<span class="stat-value">2</span>', html) 
            self.assertIn('Verified Contributions', html)
            
            # Leaderboard
            self.assertIn('Agent Smith', html)
            self.assertIn('Agent Doe', html)
            # Rogue Agent should not be in leaderboard? 
            # Logic: "is_verified = agent_name in registered_agents" -> then add to agent_contributions
            # So Rogue Agent should NOT be in leaderboard.
            self.assertNotIn('Rogue Agent</div>', html) # Assuming checks name in div

            print("Test Passed: Stats Logic Verified")

if __name__ == '__main__':
    unittest.main()
