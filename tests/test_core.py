import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from modules import supabase_client
from modules.admin_utils import calculate_admin_metrics
import pandas as pd

# Mock the supabase client
@pytest.fixture
def mock_supabase():
    with patch('modules.supabase_client.get_client') as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client

def test_calculate_admin_metrics_empty():
    df = pd.DataFrame()
    metrics = calculate_admin_metrics(df)
    assert metrics['total_bookings'] == 0
    assert metrics['upcoming_bookings'] == 0

def test_calculate_admin_metrics_data():
    data = {
        'booking_id': [1, 2],
        'appt_date': [date.today().isoformat(), '2025-01-01'],
        'email': ['a@b.com', 'b@c.com']
    }
    df = pd.DataFrame(data)
    metrics = calculate_admin_metrics(df)
    assert metrics['total_bookings'] == 2
    # Note: upcoming depends on today's date vs 2025-01-01. 
    # If today is before 2025, upcoming should be at least 1.
    
def test_create_user_success(mock_supabase):
    # Setup mock return
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{'id': '123'}]
    
    success, err = supabase_client.create_user("Test", "test@example.com", "hash")
    assert success is True
    assert err is None

def test_create_user_failure(mock_supabase):
    # Setup mock to raise exception
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")
    
    success, err = supabase_client.create_user("Test", "test@example.com", "hash")
    assert success is False
    assert "DB Error" in err

def test_save_booking_success(mock_supabase):
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{'id': 101}]
    
    bid = supabase_client.save_booking("user-uuid", "2023-10-10", "10:00", "Checkup")
    assert bid == 101

def test_save_booking_failure(mock_supabase):
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []
    
    bid = supabase_client.save_booking("user-uuid", "2023-10-10", "10:00", "Checkup")
    assert bid is None
