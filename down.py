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
import mimetypes
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
        elif arg=="--dev":
            print("using dev server instead of production")
            collections_url=collections_url.replace("clients3","chromecast-dev.sandbox")

    # create output directory
    if not os.path.exists("output"):
        os.mkdir("output")

    # fetch image collections
    request = backdrop_wallpaper_pb2.GetCollectionsRequest()
    request.language = "en-US"
    request.filtering_label.append("chromebook")
    request.filtering_label.append("google_branded_chromebook")
    
    response = requests.post(collections_url, data=request.SerializeToString(), headers={"Content-Type": "application/x-protobuf"})
    collections_response = backdrop_wallpaper_pb2.GetCollectionsResponse()
    collections_response.ParseFromString(response.content)

    # iterate over the collections and fetch the list of images within each collection
    for c in collections_response.collections:          
        print("found collection:", c.collection_name)

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
            
            # print information about the image to stdout
            message="    "+str(i.asset_id)+" ("+i.attribution[0].text+")"
            print(message.ljust(80),"... ",end="")
            sys.stdout.flush()
            
            # download the header to check if we have to download the complete image
            header = requests.head(full_url)
            mimetype = header.headers['Content-Type']
            size = int(header.headers['Content-Length'])
            destination = "output/"+c.collection_name+"/"+str(i.asset_id)+mimetypes.guess_extension(mimetype)   
            download=True
            try:
                local_size = os.path.getsize(destination)
                if local_size==size:
                    download=False
            except:
                # We get a exception if the local file does not exist
                pass
            
            # we only download the file if we don't have it locally - locally means
            # same filename and size as the remote one
            if download:
                print("downloading ... ",end="")
                try:
                    response = requests.get(full_url)
                    if response.status_code==200:
                        try:
                            output_file=open(destination,"wb")
                            output_file.write(response.content)
                            output_file.close()
                            print("done")
                        except:
                            print("failed to save downloaded image ["+destination+"]")
                            continue
                    else:
                        print("error, code was:",response.status_code)   
                except:
                    print("failed to download image from collection")
                    continue
            else:
                print("have")
                