import pandas as pd
import mock
import datetime
import boto3
import numpy

import utils
import decisionengine.framework.modules.SourceProxy as SourceProxy
import decisionengine_modules.AWS.sources.AWSSpotPriceWithSourceProxy as AWSSpotPrice

config={"channel_name": "channel_aws_config_data",
                               "Dataproducts":["spot_occupancy_config"],
                               "retries": 3,
                               "retry_timeout": 20,
    }

account = {'spot_occupancy_config': pd.read_csv('account_config.csv')}

expected_pandas_df = pd.read_csv('AWSSpotPriceWithSourceProxy_expected_acquire.csv', float_precision='high').drop_duplicates(subset=[ 'AvailabilityZone', 'InstanceType'], keep='last').reset_index(drop = True)

produces = ['provisioner_resource_spot_prices']

def fix_spot_price(df):
    out_df = df.copy(deep=True)
    for r, row in df.iterrows():
        if isinstance(row['SpotPrice'], str):
            out_df.loc[r,'SpotPrice'] = numpy.float64(row['SpotPrice'])
    return out_df

def compare_dfs(df1, df2):
    # for some reason df.equals does not work here, but if I compare cell by cell it works
    if df1.shape[0] != df2.shape[0]:
        return False
    if df1.shape[1] != df2.shape[1]:
        return False
    rc = True
    for i in range(df1.shape[0]):
        for j in range(df1.shape[1]):
            if (df1.iloc[i,j] != df2.iloc[i,j]):
                rc = False
                break
    return rc

class SessionMock(object):
    def client(self, service = None, region_name = None):
        return None
                    
class TestAWSSpotPriceWithSourceProxy:
    def test_produces(self):
        aws_s_p = AWSSpotPrice.AWSSpotPrice(config)
        assert (aws_s_p.produces() == produces)
    
    def test_acquire(self):
        aws_s_p = AWSSpotPrice.AWSSpotPrice(config)
        with mock.patch.object(SourceProxy.SourceProxy, 'acquire') as acquire:
            acquire.return_value = account
            with mock.patch.object(boto3.session, 'Session') as s:
                s.return_value = SessionMock()
                with mock.patch.object(AWSSpotPrice.AWSSpotPriceForRegion, 'get_price') as get_price:
                    sp_d = utils.input_from_file('spot_price.fixture')
                    get_price.return_value = sp_d
                    res = aws_s_p.acquire()
                    assert produces == res.keys()
                    new_df = fix_spot_price(res[produces[0]])
                    assert compare_dfs(expected_pandas_df, new_df)
