#!/usr/bin/python3
#
# Based on the offical Google Chromium sources, especially:
#
#   https://chromium.googlesource.com/chromium/src/+/master/chrome/browser/chromeos/backdrop_wallpaper_handlers/backdrop_wallpaper.proto
#   https://chromium.googlesource.com/chromium/src/+/master/chrome/browser/chromeos/backdrop_wallpaper_handlers/backdrop_wallpaper_handlers.cc
#
# first you need to run the Protocol Buffer Compiler to generate the necessary Python wrapper, by running:
#
#   cd proto
#   protoc --python_out=.. backdrop_wallpaper.proto
#

import sys
import os
import requests
import backdrop_wallpaper_pb2

if __name__=="__main__":
    # constants
    collections_url="https://clients3.google.com/cast/chromecast/home/wallpaper/collections?rt=b"
    images_url="https://clients3.google.com/cast/chromecast/home/wallpaper/collection-images?rt=b"

    # check command line arguments
    for arg in sys.argv[1:]:
        if arg=="--staging":
            print("using alpha server instead of production")
            collections_url=collections_url.replace("clients3","chromecast-staging.sandbox")

    # create output directory
    if not os.path.exists("output"):
        os.mkdir("output")

    # fetch image collections
    response = requests.post(collections_url, headers={"Content-Type": "application/x-protobuf"})
    collections_response = backdrop_wallpaper_pb2.GetCollectionsResponse()
    collections_response.ParseFromString(response.content)

    # iterate over the collections and fetch the list of images within each collection
    for c in collections_response.collections:
        print("Found collection:", c.collection_name)

        # create the destination folder for the current collection
        try:
            if not os.path.exists("output/"+c.collection_name):
                os.mkdir("output/"+c.collection_name)
        except:
            print("failed to create destination for collection")
            continue

        # retrieve all images for the collection
        try:
            backdrop_request=backdrop_wallpaper_pb2.GetImagesInCollectionRequest()
            backdrop_request.collection_id = c.collection_id
            backdrop_request.filtering_label.append("chromebook")
            backdrop_request.filtering_label.append("google_branded_chromebook")
            response=requests.post(images_url,headers={"Content-Type": "application/x-protobuf"},data=backdrop_request.SerializeToString())
        except:
            print("failed to download collection content for ["+c.collection_name+"]")
            continue

        # parse the response and fetch each individual image
        images_response = backdrop_wallpaper_pb2.GetImagesInCollectionResponse()
        images_response.ParseFromString(response.content)
        for i in images_response.images:
            full_url=i.image_url+"=s3840" # 4K resolution at max - most images retrieved are smaller
            print("    downloading image with id:", i.asset_id, "("+i.attribution[0].text+")")
            try:
                response = requests.get(full_url)
                if response.status_code==200 and response.headers['Content-Type']=='image/jpeg':
                    destination="output/"+c.collection_name+"/"+str(i.asset_id)+".jpg"
                    try:
                        output_file=open(destination,"wb")
                        output_file.write(response.content)
                        output_file.close()
                    except:
                        print("failed to save downloaded image ["+destination+"]")
                        continue
            except:
                print("failed to download image from collection")
                continue
