# FaceAge Script

This script will process a directory of images through the Microsoft Azure [Cognative
Services API](https://azure.microsoft.com/en-gb/services/cognitive-services/) [Face
API](https://docs.microsoft.com/en-us/azure/cognitive-services/face/) and save the resulting face age and emotion scores to a csv file.

## Requirements

This script requires the [requests](http://docs.python-requests.org/en/master/) library:

``` 
$ pip install requests 
```

## Configuration

The Azure Face API requires a subscription key (you can sign up for a free account
[here](https://azure.microsoft.com/en-gb/try/cognitive-services/)) which should be
specified in a `.cfg` file using the format below:

```
[Subscription]
key = 12345abcd678910efghijk
url = https://uksouth.api.cognitive.microsoft.com/face/v1.0/detect 
```

The `url` argument in the configuration file can be changed to match the closest region.
The script assumes you are using one of the free tier subscriptions so requests are rate
limited to one every 5 seconds (the limit is 20 requests per min).

## Operation

To run the script pass the configuration file, image directory and output file as
arguments to the script:

``` 
$ python faceage.py -c config.cfg -i images -o results.csv
```

The results as saved in csv file format. Values for age, gender and emotion scores are
returned for each image file along with the `faceId` value assigned by Azure.
