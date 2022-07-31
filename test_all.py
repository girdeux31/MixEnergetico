from mixenergetico import get_ree_and_request

year = 2020
month = 6
day = 8

def test_day_past():

    text = f'@MixEnergetico el {day:02d}/{month:02d}/{year-10}'  # past
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == -1
    assert request.tweet_date == f'{day:02d}/{month:02d}/{year-10}'
    assert request.start_date == f'{year-10}-06-08T00:00'
    assert request.end_date == f'{year-10}-06-08T23:59'

def test_month_past():

    text = f'@MixEnergetico el {month:02d}/{year-10}'
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == -1
    assert request.tweet_date == f'{month:02d}/{year-10}'
    assert request.start_date == f'{year-10}-06-01T00:00'
    assert request.end_date == f'{year-10}-06-30T23:59'

def test_year_past():

    text = f'@MixEnergetico el {year-10}'
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == -1
    assert request.tweet_date == f'{year-10}'
    assert request.start_date == f'{year-10}-01-01T00:00'
    assert request.end_date == f'{year-10}-12-31T23:59'
    
def test_day_future():

    text = f'@MixEnergetico el {day:02d}/{month:02d}/{year+10}'  # future
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == 502
    assert request.tweet_date == f'{day:02d}/{month:02d}/{year+10}'
    assert request.start_date == f'{year+10}-06-08T00:00'
    assert request.end_date == f'{year+10}-06-08T23:59'

def test_month_future():

    text = f'@MixEnergetico el {month:02d}/{year+10}'
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == 502
    assert request.tweet_date == f'{month:02d}/{year+10}'
    assert request.start_date == f'{year+10}-06-01T00:00'
    assert request.end_date == f'{year+10}-06-30T23:59'

def test_year_future():

    text = f'@MixEnergetico el {year+10}'
    ree, request = get_ree_and_request(text)

    assert ree.error_code == 502
    assert request.tweet_date == f'{year+10}'
    assert request.start_date == f'{year+10}-01-01T00:00'
    assert request.end_date == f'{year+10}-12-31T23:59'

def test_day_available():

    text = f'@MixEnergetico el {day}/{month}/{year}'  # available
    ree, request = get_ree_and_request(text)

    assert ree.error_code == 0
    assert round(ree.data['nuclear']['value']) == 122
    assert round(ree.data['total generation']['value']) == 670
    assert round(ree.data['total generation']['percentage']) == 100
    assert request.tweet_date == f'{day}/{month}/{year}'
    assert request.start_date == f'{year}-06-08T00:00'
    assert request.end_date == f'{year}-06-08T23:59'

def test_month_available():

    text = f'@MixEnergetico el {month}/{year}'
    ree, request = get_ree_and_request(text)

    assert ree.error_code == 0
    assert round(ree.data['nuclear']['value']) == 3621
    assert round(ree.data['total generation']['value']) == 19304
    assert round(ree.data['total generation']['percentage']) == 100
    assert request.tweet_date == f'{month}/{year}'
    assert request.start_date == f'{year}-06-01T00:00'
    assert request.end_date == f'{year}-06-30T23:59'

def test_year_available():

    text = f'@MixEnergetico el {year}'
    ree, request = get_ree_and_request(text)

    assert ree.error_code == 0
    assert round(ree.data['nuclear']['value']) == 55758
    assert round(ree.data['total generation']['value']) == 251399
    assert round(ree.data['total generation']['percentage']) == 100
    assert request.tweet_date == f'{year}'
    assert request.start_date == f'{year}-01-01T00:00'
    assert request.end_date == f'{year}-12-31T23:59'

def test_current():

    text = f'@MixEnergetico'
    ree, request = get_ree_and_request(text)
    
    assert ree.error_code == 0
 

