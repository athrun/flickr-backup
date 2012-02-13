#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Offlickr
# Hugo Haas -- mailto:hugo@larve.net -- http://larve.net/people/hugo/
# Homepage: http://larve.net/people/hugo/2005/12/offlickr/
# License: GPLv2
#
# Daniel Drucker <dmd@3e.org> contributed:
#   * wget patch
#   * backup of videos as well
#   * updated to Beej's Flickr API version 1.2 (required)

import sys
import urllib
import getopt
import time
import os.path
import threading
from xml.etree import ElementTree

# Beej's Python Flickr API
# http://beej.us/flickr/flickrapi/

from flickrapi import FlickrAPI
import logging

__version__ = '0.22+ - 2010-05-15 - Modified by Athrun'
maxTime = '9999999999'

# Gotten from Flickr

flickrAPIKey = '1391fcd0a9780b247cd6a101272acf71'
flickrSecret = 'fd221d0336de3b6d'


class Offlickr:

    def __init__(
        self,
        key,
        secret,
        uid,
        httplib=None,
        dryrun=False,
        verbose=False,
        ):
        """Instantiates an Offlickr object
        An API key is needed, as well as an API secret and a user id."""

        self.__flickrAPIKey = key
        self.__flickrSecret = secret
        self.__httplib = httplib

        # Get authentication token
        # note we must explicitly select the xmlnode parser to be compatible with FlickrAPI 1.2

#        self.fapi = FlickrAPI(self.__flickrAPIKey, self.__flickrSecret,
#                              format='xmlnode')
        self.fapi = FlickrAPI(self.__flickrAPIKey, self.__flickrSecret)
        self.fapi.token.path = '/volume1/backup_flickr/tokens'
        
        (token, frob) = self.fapi.get_token_part_one()
        if not token:
            raw_input('Press ENTER after you authorized this program')
        self.fapi.get_token_part_two((token, frob))
        self.token = token
        self.flickrUserId = uid
        self.dryrun = dryrun
        self.verbose = verbose

    def __testFailure(self, rsp):
        """Returns whether the previous call was successful"""

        if rsp.attrib['stat'] == 'fail':
            print 'Error!'
            return True
        else:
            return False

    def getPhotoList(self, dateLo, dateHi):
        """Returns a list of photo given a time frame"""

        n = 0
        flickr_max = 500
        photos = []

        print 'Retrieving list of photos'
        while True:
            if self.verbose:
                print 'Requesting a page...'
            n = n + 1
            rsp = self.fapi.photos_search(
                api_key=self.__flickrAPIKey,
                auth_token=self.token,
                user_id=self.flickrUserId,
                per_page=str(flickr_max),
                page=str(n),
                min_upload_date=dateLo,
                max_upload_date=dateHi,
                )
            if self.__testFailure(rsp):
                return None
            if rsp.find("photos").attrib['total'] == '0':
                return None
            photos += rsp.find("photos").findall("photo")
            if self.verbose:
                print ' %d photos so far' % len(photos)
            if len(photos) >= int(rsp.find("photos").attrib['total']):
                break

        return photos

    def getGeotaggedPhotoList(self, dateLo, dateHi):
        """Returns a list of photo given a time frame"""

        n = 0
        flickr_max = 500
        photos = []

        print 'Retrieving list of photos'
        while True:
            if self.verbose:
                print 'Requesting a page...'
            n = n + 1
            rsp = \
                self.fapi.photos_getWithGeoData(api_key=self.__flickrAPIKey,
                    auth_token=self.token, user_id=self.flickrUserId,
                    per_page=str(flickr_max), page=str(n))
            if self.__testFailure(rsp):
                return None
            if rsp.photos[0].attrib['total'] == '0':
                return None
            photos += rsp.find("photos").photo
            if self.verbose:
                print ' %d photos so far' % len(photos)
            if len(photos) >= int(rsp.find("photos").attrib['total']):
                break

        return photos

    def getPhotoLocation(self, pid):
        """Returns a string containing location of a photo (in XML)"""

        rsp = \
            self.fapi.photos_geo_getLocation(api_key=self.__flickrAPIKey,
                auth_token=self.token, photo_id=pid)
        if self.__testFailure(rsp):
            return None
        info = ElementTree.tostring (rsp.find("photo"), "utf-8")
        return info

    def getPhotoLocationPermission(self, pid):
        """Returns a string containing location permision for a photo (in XML)"""

        rsp = \
            self.fapi.photos_geo_getPerms(api_key=self.__flickrAPIKey,
                auth_token=self.token, photo_id=pid)
        if self.__testFailure(rsp):
            return None
        info = ElementTree.tostring (rsp.find("perms"), "utf-8")
        return info

    def getPhotosetList(self):
        """Returns a list of photosets for a user"""

        rsp = self.fapi.photosets_getList(api_key=self.__flickrAPIKey,
                auth_token=self.token, user_id=self.flickrUserId)
        if self.__testFailure(rsp):
            return None
        return rsp.find("photosets").findall("photoset")

    def getPhotosetInfo(self, pid, method):
        """Returns a string containing information about a photoset (in XML)"""

        rsp = method(api_key=self.__flickrAPIKey,
                     auth_token=self.token, photoset_id=pid)
        if self.__testFailure(rsp):
            return None
        info = ElementTree.tostring (rsp.find("photoset"), "utf-8")
        return info

    def getPhotoMetadata(self, pid):
        """Returns an array containing containing the photo metadata (as a string), and the format of the photo"""

        if self.verbose:
            print 'Requesting metadata for photo %s' % pid
        rsp = self.fapi.photos_getInfo(api_key=self.__flickrAPIKey,
                auth_token=self.token, photo_id=pid)
        if self.__testFailure(rsp):
            return None
        [source, isVideo] = self.getOriginalPhoto(rsp.find("photo").attrib['id'])
        rsp.find("photo").attrib['srcurl'] = source
        metadata = ElementTree.tostring (rsp.find("photo"), "utf-8")
        return [metadata, rsp.find("photo").attrib['originalformat']]

    def getPhotoComments(self, pid):
        """Returns an XML string containing the photo comments"""

        if self.verbose:
            print 'Requesting comments for photo %s' % pid
        rsp = \
            self.fapi.photos_comments_getList(api_key=self.__flickrAPIKey,
                auth_token=self.token, photo_id=pid)
        if self.__testFailure(rsp):
            return None
        comments = ElementTree.tostring (rsp.find("comments"), "utf-8")
        return comments

    def getPhotoSizes(self, pid):
        """Returns a string with is a list of available sizes for a photo"""

        rsp = self.fapi.photos_getSizes(api_key=self.__flickrAPIKey,
                auth_token=self.token, photo_id=pid)
        if self.__testFailure(rsp):
            return None
        return rsp

    def getOriginalPhoto(self, pid):
        """Returns a URL which is the original photo, if it exists"""

        source = None
        rsp = self.getPhotoSizes(pid)
        if rsp == None:
            return None
        for s in rsp.find ("sizes").findall ("size"):
            if s.attrib['label'] == 'Original':
                source = s.attrib['source']
        for s in rsp.find ("sizes").findall ("size"):
            if s.attrib['label'] == 'Video Original':
                source = s.attrib['source']
        return [source, s.attrib['label'] == 'Video Original']

    def __downloadReportHook(
        self,
        count,
        blockSize,
        totalSize,
        ):

        if not self.__verbose:
            return
        p = ((100 * count) * blockSize) / totalSize
        if p > 100:
            p = 100
        print '\r %3d %%' % p,
        sys.stdout.flush()

    def downloadURL(
        self,
        url,
        target,
        filename,
        verbose=False,
        ):
        """Saves a photo in a file"""

        if self.dryrun:
            return
        self.__verbose = verbose
        tmpfile = '%s/%s.TMP' % (target, filename)
        if self.__httplib == 'wget':
            cmd = 'wget -q -t 0 -T 120 -w 10 -c -O %s %s' % (tmpfile,
                    url)
            os.system(cmd)
        else:
            urllib.urlretrieve(url, tmpfile,
                               reporthook=self.__downloadReportHook)
        os.rename(tmpfile, '%s/%s' % (target, filename))


def usage():
    """Command line interface usage"""

    print 'Usage: Offlickr.py -i <flickr Id>'
    print 'Backs up Flickr photos and metadata'
    print 'Options:'
    print '\t-f <date>\tbeginning of the date range'
    print '\t\t\t(default: since you started using Flickr)'
    print '\t-t <date>\tend of the date range'
    print '\t\t\t(default: until now)'
    print '\t-d <dir>\tdirectory for saving files (default: ./dst)'
    print '\t-l <level>\tlevels of directory hashes (default: 0)'
    print '\t-p\t\tback up photos in addition to photo metadata'
    print '\t-n\t\tdo not redownload anything which has already been downloaded (only jpg checked)'
    print '\t-o\t\toverwrite photo, even if it already exists'
    print '\t-L\t\tback up human-readable photo locations and permissions to separate files'
    print '\t-s\t\tback up all photosets (time range is ignored)'
    print '\t-w\t\tuse wget instead of internal Python HTTP library'
    print '\t-c <threads>\tnumber of threads to run to backup photos (default: 1)'
    print '\t-v\t\tverbose output'
    print '\t-N\t\tdry run'
    print '\t-h\t\tthis help message'
    print '\nDates are specified in seconds since the Epoch (00:00:00 UTC, January 1, 1970).'
    print '\nVersion ' + __version__


def fileWrite(
    dryrun,
    directory,
    filename,
    string,
    ):
    """Write a string into a file"""

    if dryrun:
        return
    if not os.access(directory, os.F_OK):
        os.makedirs(directory)
    f = open(directory + '/' + filename, 'w')
    f.write(string)
    f.close()
    print 'Written as', filename


class photoBackupThread(threading.Thread):

    def __init__(
        self,
        sem,
        i,
        total,
        id,
        title,
        offlickr,
        target,
        hash_level,
        getPhotos,
        doNotRedownload,
        overwritePhotos,
        ):

        self.sem = sem
        self.i = i
        self.total = total
        self.id = id
        self.title = title
        self.offlickr = offlickr
        self.target = target
        self.hash_level = hash_level
        self.getPhotos = getPhotos
        self.doNotRedownload = doNotRedownload
        self.overwritePhotos = overwritePhotos
        threading.Thread.__init__(self)

    def run(self):
        backupPhoto(
            self.i,
            self.total,
            self.id,
            self.title,
            self.target,
            self.hash_level,
            self.offlickr,
            self.doNotRedownload,
            self.getPhotos,
            self.overwritePhotos,
            )
        self.sem.release()


def backupPhoto(
    i,
    total,
    id,
    title,
    target,
    hash_level,
    offlickr,
    doNotRedownload,
    getPhotos,
    overwritePhotos,
    ):

    print str(i) + '/' + str(total) + ': ' + id + ': '\
         + title.encode('utf-8')
    td = target_dir(target, hash_level, id)
    if doNotRedownload and os.path.isfile(td + '/' + id + '.xml')\
         and os.path.isfile(td + '/' + id + '-comments.xml')\
         and (not getPhotos or getPhotos and os.path.isfile(td + '/'
               + id + '.jpg')):
        print 'Photo %s already downloaded; continuing' % id
        return

    # Get Metadata

    metadataResults = offlickr.getPhotoMetadata(id)
    if metadataResults == None:
        print 'Failed!'
        sys.exit(2)
    metadata = metadataResults[0]
    format = metadataResults[1]
    t_dir = target_dir(target, hash_level, id)

    # Write metadata

    fileWrite(offlickr.dryrun, t_dir, id + '.xml', metadata)

    # Get comments

    photoComments = offlickr.getPhotoComments(id)
    fileWrite(offlickr.dryrun, t_dir, id + '-comments.xml',
              photoComments)

    # Do we want the picture too?

    if not getPhotos:
        return
    [source, isVideo] = offlickr.getOriginalPhoto(id)

    if source == None:
        print 'Oopsie, no photo found'
        return

    # if it's a Video, we cannot trust the format that getInfo told us.
    # we have to make an extra round trip to grab the Content-Disposition

    isPrivateFailure = False
    if isVideo:
        sourceconnection = urllib.urlopen(source)
        try:
            format = sourceconnection.headers['Content-Disposition'].split('.')[-1].rstrip('"')
        except:
            print 'warning: private videos cannot be backed up due to a Flickr bug'
            format = 'privateVideofailure'
            isPrivateFailure = True

    filename = id + '.' + format

    if os.path.isfile('%s/%s' % (t_dir, filename))\
         and not overwritePhotos:
        print '%s already downloaded... continuing' % filename
        return
    if not isPrivateFailure:
        print 'Retrieving ' + source + ' as ' + filename
        offlickr.downloadURL(source, t_dir, filename, verbose=True)
        print 'Done downloading %s' % filename


def backupPhotos(
    threads,
    offlickr,
    target,
    hash_level,
    dateLo,
    dateHi,
    getPhotos,
    doNotRedownload,
    overwritePhotos,
    ):
    """Back photos up for a particular time range"""

    if dateHi == maxTime:
        t = time.time()
        print 'For incremental backups, the current time is %.0f' % t
        print "You can rerun the program with '-f %.0f'" % t

    photos = offlickr.getPhotoList(dateLo, dateHi)
    if photos == None:
        print 'No photos found'
        sys.exit(1)

    total = len(photos)
    print 'Backing up', total, 'photos'

    if threads > 1:
        concurrentThreads = threading.Semaphore(threads)
    i = 0
    for p in photos:
        i = i + 1
        pid = str(int(p.attrib['id']))  # Making sure we don't have weird things here
        if threads > 1:
            concurrentThreads.acquire()
            downloader = photoBackupThread(
                concurrentThreads,
                i,
                total,
                pid,
                p.attrib['title'],
                offlickr,
                target,
                hash_level,
                getPhotos,
                doNotRedownload,
                overwritePhotos,
                )
            downloader.start()
        else:
            backupPhoto(
                i,
                total,
                pid,
                p.attrib['title'],
                target,
                hash_level,
                offlickr,
                doNotRedownload,
                getPhotos,
                overwritePhotos,
                )


def backupLocation(
    threads,
    offlickr,
    target,
    hash_level,
    dateLo,
    dateHi,
    doNotRedownload,
    ):
    """Back photo locations up for a particular time range"""

    if dateHi == maxTime:
        t = time.time()
        print 'For incremental backups, the current time is %.0f' % t
        print "You can rerun the program with '-f %.0f'" % t

    photos = offlickr.getGeotaggedPhotoList(dateLo, dateHi)
    if photos == None:
        print 'No photos found'
        sys.exit(1)

    total = len(photos)
    print 'Backing up', total, 'photo locations'

    i = 0
    for p in photos:
        i = i + 1
        pid = str(int(p.attrib['id']))  # Making sure we don't have weird things here
        td = target_dir(target, hash_level, pid) + '/'
        if doNotRedownload and os.path.isfile(td + pid + '-location.xml'
                ) and os.path.isfile(td + pid
                 + '-location-permissions.xml'):
            print pid + ': Already there'
            continue
        location = offlickr.getPhotoLocation(pid)
        if location == None:
            print 'Failed!'
        else:
            fileWrite(offlickr.dryrun, target_dir(target, hash_level,
                      pid), pid + '-location.xml', location)
        locationPermission = offlickr.getPhotoLocationPermission(pid)
        if locationPermission == None:
            print 'Failed!'
        else:
            fileWrite(offlickr.dryrun, target_dir(target, hash_level,
                      pid), pid + '-location-permissions.xml',
                      locationPermission)


def backupPhotosets(offlickr, target, hash_level):
    """Back photosets up"""

    photosets = offlickr.getPhotosetList()
    if photosets == None:
        print 'No photosets found'
        sys.exit(0)

    total = len(photosets)
    print 'Backing up', total, 'photosets'

    i = 0
    for p in photosets:
        i = i + 1
        pid = str(int(p.attrib['id']))  # Making sure we don't have weird things here
        print str(i) + '/' + str(total) + ': ' + pid + ': '\
             + p.find("title").text.encode('utf-8')

        # Get Metadata

        info = offlickr.getPhotosetInfo(pid,
                offlickr.fapi.photosets_getInfo)
        if info == None:
            print 'Failed!'
        else:
            fileWrite(offlickr.dryrun, target_dir(target, hash_level,
                      pid), 'set_' + pid + '_info.xml', info)
        photos = offlickr.getPhotosetInfo(pid,
                offlickr.fapi.photosets_getPhotos)
        if photos == None:
            print 'Failed!'
        else:
            fileWrite(offlickr.dryrun, target_dir(target, hash_level,
                      pid), 'set_' + pid + '_photos.xml', photos)


        # Do we want the picture too?


def target_dir(target, hash_level, id):
    dir = target
    i = 1
    while i <= hash_level:
        dir = dir + '/' + id[len(id) - i]
        i = i + 1
    return dir


def main():
    """Command-line interface"""

    # Default options

    flickrUserId = None
    dateLo = '1'
    dateHi = maxTime
    getPhotos = False
    overwritePhotos = False
    doNotRedownload = False
    target = 'dst'
    photoLocations = False
    photosets = False
    verbose = False
    threads = 1
    httplib = None
    hash_level = 0
    dryrun = False

    # Parse command line

    try:
        (opts, args) = getopt.getopt(sys.argv[1:],
                'hvponNLswf:t:d:i:c:l:', ['help'])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for (o, a) in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(0)
        if o == '-i':
            flickrUserId = a
        if o == '-p':
            getPhotos = True
        if o == '-o':
            overwritePhotos = True
        if o == '-n':
            doNotRedownload = True
        if o == '-L':
            photoLocations = True
        if o == '-s':
            photosets = True
        if o == '-f':
            dateLo = a
        if o == '-t':
            dateHi = a
        if o == '-d':
            target = a
        if o == '-w':
            httplib = 'wget'
        if o == '-c':
            threads = int(a)
        if o == '-l':
            hash_level = int(a)
        if o == '-N':
            dryrun = True
        if o == '-v':
            verbose = True

    # Check that we have a user id specified

    if flickrUserId == None:
        print 'You need to specify a Flickr Id'
        sys.exit(1)

    # Check that the target directory exists

    if not os.path.isdir(target):
        print target + ' is not a directory; please fix that.'
        sys.exit(1)

    offlickr = Offlickr(
        flickrAPIKey,
        flickrSecret,
        flickrUserId,
        httplib,
        dryrun,
        verbose,
        )

    if photosets:
        backupPhotosets(offlickr, target, hash_level)
    elif photoLocations:
        backupLocation(
            threads,
            offlickr,
            target,
            hash_level,
            dateLo,
            dateHi,
            doNotRedownload,
            )
    else:
        backupPhotos(
            threads,
            offlickr,
            target,
            hash_level,
            dateLo,
            dateHi,
            getPhotos,
            doNotRedownload,
            overwritePhotos,
            )


if __name__ == '__main__':
    main()
