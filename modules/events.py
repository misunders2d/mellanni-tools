import pandas as pd

events = {
    'PD22':['2022-07-12','2022-07-13'],
    'PFE22':['2022-10-11','2022-10-12'],
    'BFCM22':['2022-11-25','2022-11-28'],
    
    'PD23':['2023-07-11','2023-07-12'],
    'PFE23':['2023-10-10','2023-10-11'],
    'BFCM23':['2023-11-24','2023-11-27'],

    'PD24':['2024-07-16','2024-07-17'],
    'PFE24':['2024-10-08','2024-10-09'],
    'BFCM24':['2024-11-21','2024-12-02'],

    'BigSpringSale25':['2025-03-25','2025-03-31'],

    'PD25':['2025-07-08','2025-07-11'],
    'PFE25':['2025-10-07','2025-10-08'],
    'BFCM25':['2025-11-28','2025-12-01'],
    }

event_dates = {event: [pd.to_datetime(d).date() for d in pd.date_range(dates[0],dates[-1])] for event, dates in events.items()}

event_dates_list = [date for daterange in event_dates.values() for date in daterange]