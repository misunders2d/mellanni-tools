import keepa
import os
from numpy import nan
import pandas as pd
import streamlit as st
import time

KEEPA_KEY = os.getenv('KEEPA_KEY')

class KeepaProduct():
    api = keepa.Keepa(KEEPA_KEY)
    #create sales ranges (min - max)
    sales_tiers:dict = {
        -1:0,
        0: 50,
        50: 100,
        100: 200,
        200: 300,
        300: 400,
        400: 500,
        500: 600,
        600: 700,
        700: 800,
        800: 900,
        900: 1000,
        1000: 2000,
        2000: 3000,
        3000: 4000,
        4000: 5000,
        5000: 6000,
        6000: 7000,
        7000: 8000,
        8000: 9000,
        9000: 10000,
        10000: 20000,
        20000: 30000,
        30000: 40000,
        40000: 50000,
        50000: 60000,
        60000: 70000,
        70000: 80000,
        80000: 90000,
        90000:100000,
        100000: 150000}

    def __init__(self, asin=None, domain="US"):
        self.asin = input('ASIN?\n\n') if not asin else asin
        self.title = None
        self.image = None
        self.domain = domain
        self.data = None
        self.brand = None
        self.parent = None
        self._today =pd.to_datetime('today').date().strftime("%Y-%m-%d %H:%M:%S")
        self.pivot = pd.DataFrame()
        self._default_df = pd.DataFrame([0],index=[self._today],columns=['value'])
    
    def __str__(self):
        self.get_last_days(days=30)
        sales_min = int(self.last_days['sales min'].sum())
        sales_max = int(self.last_days['sales max'].sum())
        avg_price = self.last_days['final price'].mean()
        return f'{self.asin}: {self.brand}\n{self.title}\nLatest monthly sales: {sales_min} - {sales_max} units\nAverage price last 30 days: ${avg_price:.2f}'
    
    def _format_numbers(self, df):
        df['full price'] = round(df['full price'],2)
        df['final price'] = round(df['final price'],2)
        df['sales max'] = df.loc[~df['sales max'].isnull(), 'sales max'].astype(int)
        df['sales min'] = df.loc[~df['sales min'].isnull(), 'sales min'].astype(int)
        df['LD'] = round(df['LD'],2)
        return df

    def query(self):
        if not self.data:
            self.data = KeepaProduct.api.query(self.asin, domain=self.domain)
    
    def extract_from_products(self, products:list):
        self.data = [x for x in products if x['asin']==self.asin]

    #function that converts time from keepa format to datetime format
    def convert_time(self, keepa_time:int) -> pd.Timestamp:
        if keepa_time == 0:
            return 'unknown'
        converted = (keepa_time + 21564000) * 60000
        converted = pd.to_datetime(converted, unit = 'ms')
        return converted

    def apply_sales_tiers(self, x):
        if x == -1:
            return 0
        return KeepaProduct.sales_tiers[x]

    def pull_sales(self):
        if not self.data:
            self.query()
        self.title = self.data[0].get('title')
        img_links = self.data[0].get('imagesCSV')
        if img_links and len(img_links.split(','))>0:
            self.image = 'https://m.media-amazon.com/images/I/' + img_links.split(',')[0]
        self.brand = self.data[0].get('brand')
        self.parent = self.data[0].get('parentAsin')
        sales = self.data[0].get('data',{}).get('df_NEW', self._default_df)
        sales = sales.reset_index().rename(columns = {'index':'datetime','value':'full price'}).fillna(-1)
        coupons = self.data[0].get('couponHistory')
        if coupons:
            times = [self.convert_time(x) for x in coupons[::3]]
            discounts = coupons[1::3]
            perc_off = [x if x < 0 else 0 for x in discounts]
            money_off = [-x/100 if x > 0 else 0 for x in discounts]
            sns_coupons = coupons[2::3]
            coupon_history = pd.DataFrame(
                data=list(zip(times, perc_off, money_off, sns_coupons)),
                columns=['datetime', '% off','$ off','SNS']
                )
        else:
            coupon_history = pd.DataFrame({'datetime':[pd.to_datetime(self._today)],'% off':[0],'$ off':[0],'SNS':[0]})
        
        sales_history = pd.merge(sales, coupon_history, how='outer', on='datetime').ffill()#.fillna(0)
        
        lds = self.data[0].get('data',{}).get('df_LIGHTNING_DEAL', self._default_df)
        lds = lds.fillna(0)
        lds = lds.reset_index().rename(columns = {'index':'datetime','value':'LD'})
            
        sales_history = pd.merge(sales_history, lds, how='outer', on='datetime').ffill().fillna(0)
            
        bsr = self.data[0].get('data',{}).get('df_SALES', self._default_df).replace(-1,nan)
        bsr = bsr.reset_index().rename(columns = {'index':'datetime','value':'BSR'})
        sales_history = pd.merge(sales_history, bsr, how='outer', on='datetime').ffill().fillna(0)
        
        sales_history['final price'] = sales_history['full price'] * (1+ sales_history['% off']/100) - sales_history['$ off']
        sales_history.loc[sales_history['LD'] != 0, 'final price'] = sales_history['LD']
        return sales_history
       
    def pull_monthly_sold(self):
        sales_history = self.pull_sales()
        monthly_sold = self.data[0].get('monthlySoldHistory')
        if monthly_sold:
            times = [self.convert_time(x) for x in monthly_sold[::2]]
            monthly_units = monthly_sold[1::2]
            monthly_sold_history = pd.DataFrame(
                data = list(zip(times, monthly_units)),
                columns = ['datetime', 'monthlySoldMin']
                )
        else:
            monthly_sold_history = pd.DataFrame([[self._today,-1]],columns = ['datetime', 'monthlySoldMin'])
        monthly_sold_history['monthlySoldMax'] = monthly_sold_history['monthlySoldMin'].map(KeepaProduct.sales_tiers)
            
        self.sales_history_monthly = pd.merge(
            sales_history,
            monthly_sold_history,
            how='outer',
            on='datetime'
            ).ffill()
        return self.sales_history_monthly
        
    def generate_daily_sales(self):
        short_history = self.pull_monthly_sold()
        if len(short_history)==1:
            self.pivot = pd.DataFrame([[0,0,0]], columns=['final price','sales min','sales max'])
        else:
            lifetime = pd.date_range(short_history['datetime'].min(), self._today, freq='min')
            lifetime_df = pd.DataFrame(lifetime, columns=['datetime'])
            minutely_history = pd.merge(lifetime_df, short_history, how='left', on='datetime').ffill()
            #remove price info with full price == -1 product blocked
            minutely_history.loc[minutely_history['full price']==-1, 'final price'] = nan
    
            minutely_history['sales min'] = minutely_history['monthlySoldMin']/(60*24*30)
            minutely_history['sales max'] = minutely_history['monthlySoldMax']/(60*24*30)
            minutely_history['date'] = minutely_history['datetime'].dt.date
            self.pivot = minutely_history.pivot_table(
                values = [
                    'full price','% off', '$ off', 'SNS', 'LD', 'final price',
                    'sales min','sales max','BSR'
                    ],
                index = 'date',
                aggfunc = {
                    'full price':'mean',
                    '% off':'min',
                    '$ off':'min',
                    'SNS':'min',
                    'LD':'max',
                    'final price':'mean',
                    'sales min':'sum',
                    'sales max':'sum',
                    'BSR':'min'
                    }
                )
            self.pivot = self._format_numbers(self.pivot)
            self.pivot = self.pivot.replace(0,nan)
    
    def get_last_days(self, days=360):
        self.generate_daily_sales()
        
        if len(self.pivot)==1:
            self.last_days = self.pivot
        else:
            self.last_days = self.pivot[self.pivot.index >= (pd.to_datetime('today')-pd.Timedelta(days=days)).date()]
        
        

def get_tokens(api_key = KEEPA_KEY):
    api = keepa.Keepa(KEEPA_KEY)
    return api.tokens_left

def get_product_details(asins: list[str]):
    api = keepa.Keepa(KEEPA_KEY)
    tokens = api.tokens_left
    if tokens < len(asins):
        st.write('Please wait, not enough tokens to pull data from Amazon')
        time.sleep(20)
    products = api.query(asins)
    items = {}
    for p in products:
        asin = p.get('asin')
        brand = p.get('brand')
        items[asin] = {}
        title = p.get('title')
        bulletpoints = p.get('features')
        description = p.get('description')
        price = p.get('data').get('df_NEW').dropna().iloc[-1].values[0]
        coupon = p.get('coupon')
        if not coupon:
            coupon = 0
        else:
            if coupon[0] < 0:
                coupon = round(price * coupon[0] / 100,2)
            elif coupon[0] > 0:
                coupon = -coupon[0]/100
            
        sales = p.get('monthlySold')
        if not sales:
            sales = 0
            
        img_link = 'https://m.media-amazon.com/images/I/' + p.get('imagesCSV').split(',')[0]
            
        items[asin]['brand'] = brand
        items[asin]['title'] = title
        items[asin]['bulletpoints'] = '\n'.join(bulletpoints)
        items[asin]['description'] = description
        items[asin]['full price'] = price
        items[asin]['discount'] = coupon
        items[asin]['monthly sales'] = sales
        items[asin]['image'] = img_link
    return items
