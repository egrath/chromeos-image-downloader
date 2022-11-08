#!/usr/bin/python3
#
# Based on the offical Google Chromium sources, especially:
#
#   https://chromium.googlesource.com/chromium/src/+/refs/heads/main/ash/webui/personalization_app/proto/backdrop_wallpaper.proto
#   https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/browser/ash/wallpaper_handlers/wallpaper_handlers.cc
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
import argparse
import pdb

import backdrop_wallpaper_pb2

def truncate(n,decimals):
    multiplier = 10**decimals
    return int(n*multiplier) / multiplier

def debug_output(message):
    if args.debug:
        print(message)

if __name__=="__main__":
    # constants
    collections_url="https://clients3.google.com/cast/chromecast/home/wallpaper/collections?rt=b"
    images_url="https://clients3.google.com/cast/chromecast/home/wallpaper/collection-images?rt=b"

    # parse arguments from command line
    parser = argparse.ArgumentParser(description="Download Google Chrome OS Wallpapers")
    parser.add_argument("--server",default="prod",help="server to use (prod|staging|test), defaults to prod",action="store")
    parser.add_argument("--region",default="en-US",help="region to use, defaults to en-US",action="store")
    parser.add_argument("--list-collections",default=False,help="only list available collections, don't download",action="store_true")
    parser.add_argument("--unfiltered",default=False,help="don't set a request filter, default is google branded chromebook",action="store_true")
    parser.add_argument("--debug",default=False,help="Print out debugging information",action="store_true")
    args = parser.parse_args()

    # which server to use
    if args.server=="staging":
        collections_url=collections_url.replace("clients3","clients2")
        images_url=images_url.replace("clients3","clients2")
    elif args.server=="test":
        collections_url=collections_url.replace("clients3","clients1")
        images_url=images_url.replace("clients3","clients1")
    elif args.server=="prod":
        pass

    debug_output("collections_url=%s" % (collections_url))
    debug_output("images_url=%s" % (images_url))

    # create output directory
    if not os.path.exists("output"):
        os.mkdir("output")

    # fetch image collections
    request = backdrop_wallpaper_pb2.GetCollectionsRequest()
    request.language = args.region
    if not args.unfiltered:
        request.filtering_label.append("chromebook")
        request.filtering_label.append("google_branded_chromebook")
    debug_output(request)

    response = requests.post(collections_url, data=request.SerializeToString(), headers={"Content-Type": "application/x-protobuf"})
    collections_response = backdrop_wallpaper_pb2.GetCollectionsResponse()
    collections_response.ParseFromString(response.content)
    debug_output(collections_response)

    number_downloads=0
    downloads_total_size=0
    # iterate over the collections and fetch the list of images within each collection
    for c in collections_response.collections:
        print("found collection:", c.collection_name)

        if args.list_collections:
            continue

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
        debug_output(images_response)
        for i in images_response.images:
            full_url=i.image_url+"=s3840" # 4K resolution at max - most images retrieved are smaller
            debug_output("full_url=%s" % (full_url))

            # print information about the image to stdout
            message="    "+str(i.asset_id)+" ("+i.attribution[0].text+")"
            print(message.ljust(80),"... ",end="")
            sys.stdout.flush()

            # download the header to check if we have to download the complete image
            try:
                header = requests.head(full_url)
            except Exception as e:
                print("failed to download header for image [%s]" % (full_url))
                print("error was:")
                print(e)
                continue
                
            mimetype = header.headers['Content-Type']
            size = int(header.headers['Content-Length'])
            
            # we need a special handling for the jpeg mime type, which sometimes gets translated
            # to .jpe extension and at other times to .jpg, according to the mime-type given. This
            # seems to be a bug (https://bugs.python.org/issue37943)
            extension=mimetypes.guess_extension(mimetype,strict=False)
            if extension.startswith(".jpe"):
                extension=".jpg"
                
            destination = "output/"+c.collection_name+"/"+str(i.asset_id)+extension
            debug_output("destination=%s" % (destination))
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
                    response = requests.get(full_url,timeout=10)
                    if response.status_code==200:
                        try:
                            output_file=open(destination,"wb")
                            output_file.write(response.content)
                            output_file.close()
                            print("done")
                            number_downloads += 1
                            downloads_total_size += len(response.content)
                        except Exception as e:
                            print("failed to save downloaded image ["+destination+"]")
                            print("error was:")
                            print(e)
                            continue
                    else:
                        print("error, code was:",response.status_code)
                except Exception as e:
                    print("failed to download image from collection")
                    print("error was:")
                    print(e)
                    continue
            else:
                print("have")

    if not args.list_collections:
        print("# number of downloaded images:",number_downloads, "(total size:",truncate(downloads_total_size/1048576,2),"MiB)")
