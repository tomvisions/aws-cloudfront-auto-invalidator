from __future__ import print_function
import boto3
import json
import urllib
import time
import os
import time
import logging

cloudfront_client = boto3.client('cloudfront')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_cloudfront_distribution_id(bucket):
    
    bucket_origin = bucket + '.s3-website-us-east-1.amazonaws.com'
    logger.info(f"The bucket is called {bucket_origin}")
    cf_distro_id = None

    # Create a reusable Paginator
    paginator = cloudfront_client.get_paginator('list_distributions')

    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate()

    for page in page_iterator:
        for distribution in page['DistributionList']['Items']:
            for cf_origin in distribution['Origins']['Items']:
                    logger.info("Origin found {cf_origin['DomainName']}")
                    if bucket_origin == cf_origin['DomainName']:
                            cf_distro_id = distribution['Id']
                            logger.info(f"The CF distribution ID for {bucket} is {cf_distro_id})")

    return cf_distro_id

def get_size(bucket):
    command = f'/opt/aws s3 ls --summarize s3://{bucket} | grep Size'
    stream = os.popen(command)
    output = stream.read()
    oldnumber = output.strip().split(':')[1].strip()
    i = 0
    while i < 3:
        time.sleep(5)
        i += 1
        stream = os.popen(command)
        output = stream.read()
        if (oldnumber < output.strip().split(':')[1].strip()):
            return false
        else:
            logger.info("Bucket Size has not changed: Good!")

    return true

def invalidate_cloud_distribution(cf_distro_id):
    logger.info("Creating invalidation for {key} on Cloudfront distribution {cf_distro_id}")

    try:
        invalidation = cloudfront_client.create_invalidation(DistributionId=cf_distro_id,
                                                             InvalidationBatch={
                                                                 'Paths': {
                                                                     'Quantity': 1,
                                                                     'Items': [
                                                                         '/*'
                                                                     ]
                                                                 },
                                                                 'CallerReference': str(time.time())
                                                             })

        logger.info(f"Submitted invalidation. ID {invalidation['Invalidation']['Id']} Status {invalidation['Invalidation']['Status']}")

    except Exception as e:
        logger.info(f"Error processing object {key} from bucket {bucket}. Event {json.dumps(event, indent=2)}")
        raise e

# --------------- Main handler ------------------
def lambda_handler(event, context):
    '''
    Creates a cloudfront invalidation for content added to an S3 bucket
    '''
    # Log the the received event locally.
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event.

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    if not (get_size(bucket)):
        quit()


#    s3_resource.Object(bucket, key).delete()
    cf_distro_id = get_cloudfront_distribution_id(bucket)

    if cf_distro_id:
        invalidate_cloud_distribution(cf_distro_id)
    else:
        logger.info(f"Bucket {bucket} does not appeaer to be an origin for a Cloudfront distribution")

    return 'Success'
