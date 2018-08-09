
import feedparser
import boto3
import json

from time import mktime
from datetime import datetime

from boto3.dynamodb.conditions import Key, Attr

def smart_truncate(content, length=100, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

def process_rss():

    ddb = boto3.resource('dynamodb', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')
    
    announces = ddb.Table('whatsnew_announces')
    
    feed = feedparser.parse('https://aws.amazon.com/new/feed/')
    
    for entry in feed['entries']:
    
        # is the feed already in DDB table?
        try: 
            response = announces.get_item(Key={'id': entry['id']})
            if response['Item'] is not None:
                print("RSS {} is already in the DB, skipping".format(entry['id']))
        
        except KeyError:
            # Item is not there, add it and notify
            try:
                published = datetime.fromtimestamp(mktime(entry['published_parsed']))
                response = sns.publish(
                        TopicArn='arn:aws:sns:us-east-1:469769735412:aws_whatsnew',
                        Message=json.dumps({'id': entry['id'], 'title': entry['title'], 'published': published.isoformat(), 'link': entry['link']}),
                        Subject=smart_truncate(entry['title'], length=80)
                )
                announces.put_item(Item={'id': entry['id'], 'title': entry['title'], 'published': published.isoformat(), 'link': entry['link']})
                print("Published message: {}".format(response['MessageId']))
            except Exception as ex:
                print("Something went wrong publishing {}: {}".format(entry['id'], ex))
    print("Finished processing")

def lambda_handler(event, context):
    process_rss()

if __name__ == '__main__':
    process_rss()
