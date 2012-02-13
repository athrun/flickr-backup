#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import glob
from xml.etree import ElementTree

BASEDIR = "/volume1/photo"
PHOTOSETDIR = "./sets"
PHOTODIR = "./content"

def parse_sets_info ():
	if not os.path.isdir (PHOTOSETDIR):
		print "%s folder was not found!" % PHOTOSETDIR
	        sys.exit (2)
	if not os.path.isdir (PHOTODIR):
		print "%s folder was not found!" % PHOTODIR
	        sys.exit (2)
	sets_path_list = glob.glob ("%s/set_*_info.xml" % PHOTOSETDIR)
	print "%s photosets found." % len (sets_path_list)
	sets_list = []
	for path in sets_path_list:
		photoset_element = ElementTree.parse (path).getroot ()
		photoset_id = photoset_element.attrib.get ("id")
		photoset_name = photoset_element.find ("title").text
		photoset_description = photoset_element.find ("description").text
		photosetcontent_element = ElementTree.parse ("%s/set_%s_photos.xml"  
							% (PHOTOSETDIR, photoset_id)).getroot ()
		photo_id_list = []
		for photo_element in photosetcontent_element.findall ("photo"):
			photo_id_list.append (photo_element.attrib.get ("id"))
		sets_list.append ({
			"id": photoset_id,
			"name": photoset_name,
			"description": photoset_description,
			"photos": photo_id_list
		})
	return sets_list
	
def generate_links (sets_list):
	for set in sets_list:
		print "Generating links for set %s [%i items]" % (set ["name"].encode ("utf-8"), len (set ["photos"]))
		os.mkdir (os.path.join (BASEDIR, set ["name"].encode ("utf-8")))
		for photo_id in set ["photos"]:
			if os.path.isfile (os.path.join (PHOTODIR, "%s.jpg" % photo_id )):
				os.link (os.path.realpath (os.path.join (PHOTODIR, "%s.jpg" % photo_id )),
			        	    os.path.join (BASEDIR, set ["name"].encode ("utf-8"), "%s.jpg" % photo_id))
			elif os.path.isfile (os.path.join (PHOTODIR, "%s.png" % photo_id )):
				os.link (os.path.realpath (os.path.join (PHOTODIR, "%s.png" % photo_id )),
			        	    os.path.join (BASEDIR, set ["name"].encode ("utf-8"), "%s.png" % photo_id))
			elif os.path.isfile (os.path.join (PHOTODIR, "%s.mpg" % photo_id )):
				os.link (os.path.realpath (os.path.join (PHOTODIR, "%s.mpg" % photo_id )),
			        	    os.path.join (BASEDIR, set ["name"].encode ("utf-8"), "%s.mpg" % photo_id))
			else:
				print "Don't know what to do of %s in set %s." % (photo_id, set ["name"].encode ("utf-8"))
			        	    
def check_n_clean_basedir ():
	if not os.path.isdir (BASEDIR):
		print "%s folder was not found!" % BASEDIR
		sys.exit (2)
	print "CAUTION: The entire content of %s is going to be REMOVED." % os.path.realpath (BASEDIR)
	print "Do you want to continue? [Y]es or [N]o"
	key = raw_input ("> ")
	if key.lower () != 'y':
		sys.exit (0)
	content = os.listdir (BASEDIR)
	print "Deleting %s items..." % len (content)
	for folder in content:
		if folder.startswith ("@eaDir"):
			continue
		folder_path = os.path.realpath (os.path.join (BASEDIR, folder))
		shutil.rmtree (folder_path, False, _rmtree_error_handler)
	
def _rmtree_error_handler (function, path, excinfo):
	print "error: %s %s %s" % (function, path, excinfo)

def main ():
	check_n_clean_basedir ()
	sets_list = parse_sets_info ()
	generate_links (sets_list)


if __name__ == '__main__':
	main ()
