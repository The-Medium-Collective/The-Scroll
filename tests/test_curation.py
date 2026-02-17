import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock dependencies
mock_github = MagicMock()
sys.modules['github'] = mock_github
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase

from app import app, CORE_ROLES, is_core_team

class TestCurationSystem(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Set Master Key env
        os.environ['AGENT_API_KEY'] = 'MASTER_KEY_123'

    def tearDown(self):
        if 'AGENT_API_KEY' in os.environ:
             del os.environ['AGENT_API_KEY']

    def test_multi_role_check(self):
        # Test helper directly
        mock_client = MagicMock()
        with patch('app.supabase', mock_client):
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'role': 'curator'}])
            self.assertTrue(is_core_team('SimpleAgent'))

    def test_curation_master_key_bypass(self):
        mock_client = MagicMock()
        with patch('app.supabase', mock_client):
             # Mock Agent Existence Check (for FK)
            # We need to return data when checking for agent existence
            mock_agent_check = MagicMock(data=[{'name': 'MasterAgent'}])
            
            # Mock Vote Insert
            mock_insert = MagicMock()
            
            def side_effect(table_name):
                 mock_table = MagicMock()
                 if table_name == 'agents':
                     # The code does: select('name').eq('name', agent_name).execute()
                     mock_table.select.return_value.eq.return_value.execute.return_value = mock_agent_check
                 elif table_name == 'curation_votes':
                     # Check existing vote
                     mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                     # Insert
                     mock_table.insert.return_value.execute.return_value = mock_insert
                     # Count votes
                     mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                 return mock_table
                 
            mock_client.table.side_effect = side_effect
            
            # Request using Master Key
            response = self.app.post('/api/curate', 
                                    headers={'X-API-KEY': 'MASTER_KEY_123'},
                                    json={'agent': 'MasterAgent', 'pr_number': 99, 'vote': 'approve'})
                                    
            self.assertEqual(response.status_code, 200)
            self.assertIn('Vote recorded', response.get_json()['message'])

    def test_curation_master_key_fail_if_agent_not_found(self):
         mock_client = MagicMock()
         with patch('app.supabase', mock_client):
             # Mock Agent NOT FOUND
             mock_agent_check = MagicMock(data=[]) # Empty list
             
             mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_agent_check
             
             response = self.app.post('/api/curate', 
                                    headers={'X-API-KEY': 'MASTER_KEY_123'},
                                    json={'agent': 'GhostAgent', 'pr_number': 99, 'vote': 'approve'})
             
             # Should fail with 400 because agent must exist for FK
             self.assertEqual(response.status_code, 400)
             self.assertIn('Agent not registered', response.get_json()['error'])
                
if __name__ == '__main__':
    unittest.main()
