#This code finds faces from an image, crops the faces, searches the faces in the AWS collection and adds them to a s3 bucket
#if the image is not found in the collection

from boto.s3.connection import S3Connection
import os
import boto3
from PIL import Image
import sys
import botocore
import io

COLLECTION = str(os.environ.get('COLLECTION'))

def findFaces(collection, srcBucket, srcKey):
    client = boto3.client('rekognition')
    #Find faces in the image
    response = client.detect_faces(
        Image={
            'S3Object': {
                'Bucket': srcBucket,
                'Name': srcKey
            }
        },
        )

    print 'Number of faces:',len(response['FaceDetails'])
    if len(response['FaceDetails'])!=0:
        crop(response,srcBucket,srcKey)
    else:
        return 'no faces'


def crop(data, srcBucket, srcKey):
    s3 = boto3.resource('s3')
    #Download image to local
    try:
        s3.Bucket(srcBucket).download_file(srcKey, 'imageToCrop.jpg')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    # Load the original image:
    img = Image.open("imageToCrop.jpg")

    for i in range (0,len(data['FaceDetails'])):
        width = data['FaceDetails'][i]['BoundingBox']['Width']
        height = data['FaceDetails'][i]['BoundingBox']['Height']
        left = data['FaceDetails'][i]['BoundingBox']['Left']
        top =  data['FaceDetails'][i]['BoundingBox']['Top']

        widImage = img.size[0]
        htImage = img.size[1]
        img1 = img.crop((left * widImage,top * htImage ,left * widImage + width * widImage,top * htImage + height * htImage))

        key = srcKey.replace('/',"")
        #naming the image
        tmpCropped = 'cropped_'+str(i)+key
        #Changing image to bytes
        imgByteArr = io.BytesIO()
        img1.save(imgByteArr, format='JPEG')
        imgByteArr = imgByteArr.getvalue()

        response = searchImageinCollection(COLLECTION, srcBucket, imgByteArr)
        #If no matches found add the image to test folder
        if len(response['FaceMatches'])==0:
            print 'alert'
            name = 'test/'+tmpCropped
            #put object in bucket
            object = s3.Bucket(srcBucket).put_object(Body = imgByteArr, Key = name)



def searchImageinCollection(collection, srcBucket, imgBytes):
    client = boto3.client('rekognition')
    #Search image in collection
    response = client.search_faces_by_image(
        CollectionId=collection,
        Image={
            'Bytes': imgBytes,

        },
    )
    return response



if __name__ == '__main__':
  # Code For the lambda_handler
  #srcBucket = event["Records"][0]['s3']['bucket']['name']
  #srcKey = urllib.unquote(event["Records"][0]['s3']['object']['key'].replace("+", " "))
  srcBucket = str(os.environ.get('LOCAL_BUCKET'))
  srcKey = str(os.environ.get('FILE'))
  findFaces(COLLECTION,srcBucket,srcKey)