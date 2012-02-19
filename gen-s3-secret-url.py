#!/usr/bin/env python

import sys
import argparse
from boto.s3.connection import S3Connection
from urlparse import urlparse
from ConfigParser import ConfigParser
from paver.easy import path


def setup_argparse ():
    parser = argparse.ArgumentParser (description="Generate a signed URL to a object stored in Amazon S3.")
    parser.add_argument ("url", type=unicode, help="S3 URL to sign. Formated like s3://my-bucket/path/to/key")
    parser.add_argument ("-e", "--expires", metavar="seconds", type=int, dest="expires_in", default=86400, help="Number of seconds after which the link will expire. (Default: 1 day)")
    return parser.parse_args ()

def parse_s3config ():
    s3config = path (__file__).realpath ().dirname () / "s3cmd.ini"
    if not s3config.exists ():
        print "Unable to read %s. Exiting." % s3config
        sys.exit (1)
    config = ConfigParser ()
    config.read (s3config)
    return (config.get ("default", "access_key"), config.get ("default", "secret_key"))

if __name__ == "__main__":
    args = setup_argparse ()
    (s3_access_key, s3_secret_key) = parse_s3config ()

    res = urlparse (args.url)
    if not res.scheme == "s3":
        print "Invalid URL: %s" % args.url
        print "URL scheme should be: s3://bucket-name/path/to/object"
        sys.exit (1)

    s3 = S3Connection (s3_access_key, s3_secret_key, is_secure=True)
    print s3.generate_url (args.expires_in, 'GET', res.netloc, res.path, force_http=True)
