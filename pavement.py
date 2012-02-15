# -*- coding: utf-8 -*-
#
# This file designed to work with the Paver build tool
# see: http://paver.github.com/paver/
#
from paver.easy import *
import sys, os
import shutil
import glob
import ConfigParser
from xml.etree import ElementTree

@task
def auto ():
    """ Initialization task.
    """
    # Read the config.ini file
    config_file = path (__file__).realpath ().dirname () / "config.ini"
    config = ConfigParser.ConfigParser ()
    config.read (config_file)
    options.update (config.items ("backup"))
    
    # Define all the folders we require
    folders = [{"backup_dir": path (options.backup_dir)},
               {"sets_dir": path (options.backup_dir) / "sets"},
               {"content_dir": path (options.backup_dir) / "content"},
               {"tokens_dir":  path (options.backup_dir) / "tokens"},
               {"album_output_dir": path (options.album_output_dir)}]
    
    # Make sure the folders are created
    # and populate the config options
    for item in folders:
        [d.mkdir () for d in item.values ()]
        options.update (item)
    
    # Set the env var pointing to the token dir
    os.environ ["FLICKR_TOKEN_DIR"] = options.tokens_dir

@task
def backup_sets ():
    """ Backup flickr sets information.
    """
    sh_v ("./offlickr.py -s -d '%s' -i %s" % (options.sets_dir, options.flickr_uid))

@task
def backup_content ():
    """ Backup flickr content (actual photo & video files).
    """
    sh_v ("./offlickr.py -p -n -d '%s' -i %s" % (options.content, options.flickr_uid))  

@task
@needs (["backup_sets", "backup_content"])
def backup_flickr ():
    """Backup flickr sets & content.
    """
    pass

@task
def clean_photo_dir ():
    """ Cleanup the photo album directory.
    """
    def rmtree_error_handler (function, path, excinfo):
        print "error: %s %s %s" % (function, path, excinfo)

    if not os.path.isdir (options.album_output_dir):
        print "%s folder was not found!" % options.album_output_dir
        sys.exit (2)
    print "CAUTION: The entire content of %s is going to be REMOVED." \
            % os.path.realpath (options.album_output_dir)
    print "Do you want to continue? [Y]es or [N]o"
    key = raw_input ("> ")
    if key.lower () != 'y':
        sys.exit (0)
    content = os.listdir (options.album_output_dir)
    print "Deleting %s items..." % len (content)
    for folder in content:
        if folder.startswith ("@eaDir"):
            continue
        folder_path = os.path.realpath (os.path.join (options.album_output_dir, folder))
        shutil.rmtree (folder_path, False, rmtree_error_handler)

@task
@needs (["clean_photo_dir"])
def generate_album ():
    """ Generates hard links in the photo album directory.
    Links point back to the actual content located in this
    backup directory.
    """
    album_output_dir = options.album_output_dir
    sets_dir = path (options.backup_dir) / "sets"
    content_dir = path (options.backup_dir) / "content"
    sets_list = parse_sets_info (sets_dir, content_dir)
    for set in sets_list:
        print "Generating links for set %s [%i items]" % (set ["name"].encode ("utf-8"),
                                                          len (set ["photos"]))
        os.mkdir (os.path.join (album_output_dir, set ["name"].encode ("utf-8")))
        for photo_id in set ["photos"]:
            if os.path.isfile (os.path.join (content_dir, "%s.jpg" % photo_id )):
                os.link (os.path.realpath (os.path.join (content_dir, "%s.jpg" % photo_id )),
                         os.path.join (album_output_dir, set ["name"].encode ("utf-8"), "%s.jpg" % photo_id))
            elif os.path.isfile (os.path.join (content_dir, "%s.png" % photo_id )):
                os.link (os.path.realpath (os.path.join (content_dir, "%s.png" % photo_id )),
                         os.path.join (album_output_dir, set ["name"].encode ("utf-8"), "%s.png" % photo_id))
            elif os.path.isfile (os.path.join (content_dir, "%s.mpg" % photo_id )):
                os.link (os.path.realpath (os.path.join (content_dir, "%s.mpg" % photo_id )),
                         os.path.join (album_output_dir, set ["name"].encode ("utf-8"), "%s.mpg" % photo_id))
            else:
                print "Don't know what to do of %s in set %s." % (photo_id, set ["name"].encode ("utf-8"))

# No tasks below this point.
def sh_v(command, ignore_error=False, cwd=None):
    """Runs an external command. If the command
    has a non-zero return code raise a BuildFailure. You can pass
    ignore_error=True to allow non-zero return codes to be allowed to
    pass silently, silently into the night.  If you pass cwd='some/path'
    paver will chdir to 'some/path' before exectuting the command.

    If the dry_run option is True, the command will not
    actually be run."""
    def runpipe():
        kwargs = { 'shell': True, 'cwd': cwd}
        p = subprocess.Popen(command, **kwargs)
        p_stdout = p.communicate()[0]
        if p.returncode and not ignore_error:
            raise BuildFailure("Subprocess return code: %d" % p.returncode)

    return dry(command, runpipe)

def parse_sets_info (sets_dir, content_dir):
    if not os.path.isdir (sets_dir):
        print "%s folder was not found!" % sets_dir
        sys.exit (2)
    if not os.path.isdir (content_dir):
        print "%s folder was not found!" % content_dir
        sys.exit (2)
    sets_path_list = glob.glob ("%s/set_*_info.xml" % sets_dir)
    print "%s photosets found." % len (sets_path_list)
    sets_list = []
    for path in sets_path_list:
        photoset_element = ElementTree.parse (path).getroot ()
        photoset_id = photoset_element.attrib.get ("id")
        photoset_name = photoset_element.find ("title").text
        photoset_description = photoset_element.find ("description").text
        photosetcontent_element = ElementTree.parse ("%s/set_%s_photos.xml"  
                                    % (sets_dir, photoset_id)).getroot ()
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
    
