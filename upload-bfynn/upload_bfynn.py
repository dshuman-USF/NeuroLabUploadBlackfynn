#!/usr/bin/env python3

'''
This is a table driven program that uses a .csv file to map your file system's
organization and naming conventions to the MAP-Core file system and naming
conventions. The .csv file format is documented in:

     TEMPLATE-for-SPARC-list-of-files-to-upload.xlsx

It creates the required directory hierearchy as specified by:
https://docs.google.com/presentation/d/1EQPn1FmANpPsFt3CguU-JOQVMMlJsNXluQAK_gb2qVg/edit#slide=id.p1

The dataset must already exist and you need to have an API key. That process is
documented here:

https://developer.blackfynn.io/python/latest/index.html

The program creates collections if required and uploads local files to the
Blackfynn site. Collections and datapackages are renamed according to the
standards.

This can be run from a command line window.
Most users should use upload_bfynn_win.pyw program.
This provies a GUI wrapper that uses this class.

Copyright (c) 2019 by Kendall F. Morris
kmorris5@usf.edu
License: GPLv3 or later.
Maintainer: Dale Shuman
dshuman@usf.edu
Thu 07 Nov 2019 01:28:14 PM EST
'''

import os
import csv
import glob
import sys
import time
from datetime import timedelta
from blackfynn import Blackfynn, Settings
from blackfynn.models import Collection
from blackfynn.api.agent import AgentError

__version__ = '1.0.17'

class UploadBlackfynn:
    """
    Command line class to upload files to Blackfynn datasets.
    """
    PREFIXES = {
        'primary':     'sub-',
        'derivative':  'sub-',
        'samples':     'sam-',
        'session':     'ses-',
        'performance': 'perf-',
        'pool':        'pool-',
        'source':      'sub-'
        }

    # Files with these names will not be renamed
    PROTECTED_NAMES = [
        'subjects.csv',
        'samples.csv',
        'dataset_description.csv',
        'submission.csv',
        'Readme',
        'Changes',
        'manifest.csv'
        'manifest.xls'
        'manifest.xlsx'
        ]

    # Input csv file column and row offsets
    # First real data row is destination dataset
    ROWS_TO_NAME = 3
    DATASET_NAME = 0
    ROWS_TO_DSET = 4
    TOP_LEVEL = 0
    SUBJ = 1
    SESSID = 2
    DESTFOLD = 3
    SRCFILE = 4

    def __init__(self):
        self._profile_name = None    # users of class must set most of these
        self._csv_name = None
        self._dataset_name = None
        self._stop_right_now = False
        self._b_fynn = None
        self._dataset = None
        self._uploaded = 0
        self._use_agent = False
        self._add_ext = True
        self.overwrite = None

    def set_csv(self, csv_name):
        '''
        The gui wrapper needs to set this. It could just write directly
        to the name, but seems like this makes it more obvious.
        '''
        self._csv_name = csv_name
        self._get_dataset_name()

    def set_profile(self, profile_name):
        '''
        The gui wrapper needs to set this. It could just write directly
        to the profile_name, but seems like this makes it more obvious.
        '''
        self._profile_name = profile_name

    def set_add_ext(self, state):
        '''
        The gui wrapper lets the user choose to add or not add the
        original file extensions while renaming a dataset.
        '''
        self._add_ext = state

    def set_use_agent(self, state):
        '''
        The gui wrapper lets the user choose to user BF agent or not.
        '''
        self._use_agent = state

    def curr_dataset(self):
        '''
        The gui wrapper needs this name. Return it.
        '''
        return self._dataset_name

    def set_overwrite(self, callback):
        '''
        callback from the gui part of this package.
        we use this to request an overwrite of the
        current line, as opposed to just printing,
        which goes through stdout.
        '''
        self.overwrite = callback

    @staticmethod
    def get_profile_list():
        """
        The gui wrapper needs the list
        """
        settings = Settings()
        list_profile = []
        for item in settings.profiles.items():
            if item[0] not in ['global']:
                if item[1]['api_token']:
                    list_profile.append(item[0])
        return list_profile


    def chk_files_exist(self):
        '''
        Returns True if all the files in the .csv file exist. False if not.
        Wildcards supported in file names, not dirs, no recursion.
        '''
        if not self._csv_name:
            print("No .csv file selected, nothing to check\n")
            return False
        okay = True
        print('Making sure that files to upload exist. . .', end='')
        with open(self._csv_name) as csvfile:
            fnames = csv.reader(csvfile, delimiter=',')
            for row in range(self.ROWS_TO_DSET):  # skip info in first rows
                try:
                    next(fnames)
                except Exception as ex:
                    print('Error reading row {} of {} file, '
                          'error is {}.'.format(row, self._csv_name, str(ex)))
            # turn list(s) of files into one list of strings
            files = [file for file in [name[self.SRCFILE] for name in fnames]
                     if file and not file.isspace()]
            # Remove optional leading and trailing grouping brackets
            files = [fn.strip('[]') for fn in files]
            files = ','.join(files).split(',')
            for check in files:
                pathchk = os.path.dirname(check)
                if pathchk and any(wild in '*?' for wild in pathchk):
                    print('This program does not support wildcards'
                          'in path names (okay in file names), skipping .' + pathchk)
                    continue
                expanded_files = glob.glob(check)
                if not expanded_files:
                    print('\nThe path {} or the file {} does not exist.'.format(
                        pathchk, os.path.basename(check)), end='')
                    okay = False
        if okay:
            print('looking good!')
        return okay

    def _chk_on_blackfynn(self, collection, fname):
        '''
        Check to see if the fname exists in the current collection by looking
        at the sources attribute.
        '''
        have_file = False
        for item in collection:
            if isinstance(item, Collection):
                continue
            if not item.sources:
                item = self._okay_to_update(item) # if re-running program
                                                  # pkg may not be ready yet
            true_names = item.sources
            if not true_names:
                print('Data package available, but source attribute not available.')
            for lookup in true_names:
                realfile = os.path.basename(lookup.s3_key)
                if realfile == fname:
                    have_file = True
                    break
            if have_file:
                break
        return have_file


    @staticmethod
    def _make_file_list(src_file):
        '''
        For single path/file, build a list of individual names, each in a list.
        For multi-path/files, inner list contains all of the matches.
        '''
        expanded_files = []
        multi_list = []
        keep_together = src_file[0] == '[' and src_file[-1] == ']'
        files = src_file.strip('[]')
        files = files.split(',')
        multi = len(files) > 1
        for check in files:
            pathchk = os.path.dirname(check)
            if pathchk and any(wild in '*?' for wild in pathchk):
                continue
            flist = glob.glob(check)
            if not flist:
                print('The path or file', check, ' does not exist')
                continue
            if multi:
                for fname in flist:
                    multi_list.append(fname)
            else:
                expanded_files.append(flist)
        if multi_list:
            if keep_together:
                expanded_files.append([multi_list])
            else:
                expanded_files.append(multi_list)
        return expanded_files


    def chk_exist(self, collection, dest_copy, fname, dest_name):
        '''
        Check to see if file is already on blackfynn site.
        Complain if so.
        '''
        if self._chk_on_blackfynn(collection, dest_copy):
            print('File {} already uploaded to {}.'.format(fname, dest_name))
            print('Delete it in a browser to re-upload it.', flush=True)
            return True
        return False


    def _upload_singles(self, collection, files, prefix, name):
        '''
        Upload a group of files one by one to the collection.
        Expects a list of strings.
        '''
        for next_file in files:
            if self._stop_right_now:
                return
            dest_copy = os.path.basename(next_file)
            if self.chk_exist(collection, dest_copy, next_file, name):
                continue
            print('Uploading', next_file, ' to', name)
            start = time.time()
            try:
                collection = self._wait_for_ready(collection)
                res = collection.upload(next_file, use_agent=self._use_agent, display_progress=True)
                end = time.time()
                print('Elapsed time:', (str(timedelta(seconds=end-start))))
                self._uploaded += 1
            except AgentError as ex:
                print('AGENT ERROR: {}'.format(str(ex)))
                self._stop_right_now = True
                return
            except Exception as ex:
                print('Error uploading {} to collection {}. '
                      'Error was {}.'.format(next_file, collection.name, str(ex)))
                end = time.time()
                print('Elapsed time: ', str(timedelta(seconds=end-start)))
                return
            self.name_conform(res, [next_file], collection, prefix)


    def _upload_group(self, collection, files, prefix, name):
        '''
        Upload a group of files in a single operation . Expects a list of list(s)
        If any file in the group already exists on the blackfynn site, bail. It
        is all or nothing for a group.
        '''
        for next_file in files:
            if self._stop_right_now:
                return
            dest_copy = os.path.basename(next_file)
            if self.chk_exist(collection, dest_copy, next_file, name):
                return
            continue

        print('Uploading', files, ' to', name)
        start = time.time()
        try:
            collection = self._wait_for_ready(collection)
            res = collection.upload(files, use_agent=self._use_agent, display_progress=True)
            end = time.time()
            print('Elapsed time: ', str(timedelta(seconds=end-start)))
            self._uploaded += len(files)
        except AgentError as ex:
            print('AGENT ERROR: {}'.format(str(ex)))
            self._stop_right_now = True
            return
        except Exception as ex:
            print('Error uploading {} to collection {}.,'
                  'Error was {}.'.format(files, collection.name, str(ex)))
            end = time.time()
            print('Elapsed time: ', str(timedelta(seconds=end-start)))
            return
        self.name_conform(res, files, collection, prefix)


    def _upload_list(self, collection, files, prefix, name):
        ''''
        Upload list of files to the collection, rename
        by adding optional prefix when mapcore standards require it .
        Item in list can be name(s), or a list of name(s).
        List of names are uploaded one name at a time.
        A list containing a list of names is uploaded as a unit.
        '''
        for file_list in files:
            # item in list can be name(s), or a list of name(s)
            if isinstance(file_list[0], str):
                files = [file for file in file_list]
                self._upload_singles(collection, files, prefix, name)
            elif isinstance(file_list[0], list):
                files = [file for fn in file_list for file in fn]
                self._upload_group(collection, files, prefix, name)
            else:
                print('Unexpected type of file list')
                return


    def _collection_chk(self, collection, paths):
        '''
        Find or create one or more collections in a collection hierarchy
        and return the lowest collection. Since files and folder can have
        same name, make sure we only look at collections.
        '''
        hier = paths.split('/')
        for level in hier:
            for curr_coll in collection.items:
                if isinstance(curr_coll, Collection) and curr_coll.name == level:
                    break
            else:
                print('Creating', level, 'in', collection.name)
                # Note: Sometimes this fails for UF folk late at night
                # when doing unattended uploads.
                # The code that raises the error is:
                # raise HTTPError(http_error_msg, response=self)
                try:
                    curr_coll = collection.create_collection(level)
                except Exception as ex:
                    print('Error creating collection {},\n'
                          'error is {}.'.format(collection.name, str(ex)))
            curr_coll = self._wait_for_ready(curr_coll)
            collection = curr_coll  # step down into new collection
        return curr_coll


    def _get_dataset_name(self):
        '''
        The destination dataset name is in the .csv file. Get it and
        stuff into class var.
        '''
        working_dset = ''
        with open(self._csv_name) as csvfile:
            in_file = csv.reader(csvfile, delimiter=',')
            for row in range(self.ROWS_TO_NAME):  # skip info rows
                try:
                    next(in_file)
                except UnicodeDecodeError as ex:
                    print('Error reading row {} of {} file,\n'
                          'error is {}.'.format(row, self._csv_name, str(ex)))
                    print('If you are using excel, save the file as a CSV (MS-DOS) .csv file')
                    print('Unable to read the .csv file, upload aborted.')
                    return ''
                except Exception as ex:
                    print('Error reading row {} of {} file,\n'
                          'error is {}.'.format(row, self._csv_name, str(ex)))
                    print('Unable to read the .csv file, upload aborted.')
                    return ''
            row = next(in_file)
            working_dset = row[self.DATASET_NAME]
        self._dataset_name = working_dset
        return working_dset


    def _get_csv(self,):
        '''
        Show csv files in current dir and get name of one you want.
        If no csv, prompt for path and file.
        '''
        list_csv = glob.glob('*.csv')
        list_csv.sort()
        print()
        print('Select a .csv file')
        self._csv_name = ''
        if list_csv:
            choice = 1
            for cfile in list_csv:
                print('   ', choice, cfile)
                choice += 1
            choice = input('Enter number from list or path and name to csv file: ')
            if choice.isnumeric():
                offset = int(choice)-1
                if 0 <= offset < len(list_csv):
                    working_csv = list_csv[offset]
        else:
            working_csv = input('Enter path and csv file name: ')
        if working_csv and not os.path.exists(working_csv):
            print('The file', working_csv, ' does not exist.')
            working_csv = ''
        self._csv_name = working_csv


    def get_profile(self):
        '''
        Scan local config, show profiles, pick one.
        Bad news if no profile, is there any other way to get credentials?
        '''
        list_profile = self.get_profile_list()
        print()
        if list_profile:
            print('Select a Blackfynn profile')
            choice = 1
            for prof in list_profile:
                print('   ', choice, prof)
                choice += 1
            choice = input('Enter number from list to select profile to use: ')
            if choice.isnumeric():
                offset = int(choice)-1
                if 0 <= offset < len(list_profile):
                    self._profile_name = list_profile[offset]
                else:
                    self._profile_name = ''
        else:
            print('Cannot find a profile on this system. You need to use the bf program',
                  'to create a profile')
            sys.exit('Uploading aborted.')

    def _get_add_ext(self):
        '''
        We will tack on the original file extensions by default, but the
        user may not want to.
        '''
        print()
        print('Do you want the original file name extension to be',
              'added to the datapackage name?')
        choice = input('Type y for yes, anything else for no: ')
        if choice in ('y', 'Y'):
            self._add_ext = True
        else:
            self._add_ext = False

    def _get_use_agent(self):
        '''
        The blackfynn upload agent does not return any info, unlike the api call.
        We prefer to not use the agent, but if an upload takes longer than an
        hour, the agent is they way to go.
        '''
        print()
        print('If uploading a file takes longer than an hour, you need to use',
              'the Blackfynn agent.\nDo you want to use the Blackfynn agent?', end='')
        choice = input('Type y for yes, anything else for no: ')
        if choice in ('y', 'Y'):
            self._use_agent = True


    def _get_prefix(self, level_name):
        '''
        If the name has a prefix, return it, empty str otherwise.
        '''
        try:
            prefix = self.PREFIXES[level_name]
        except KeyError:
            prefix = ''
        return prefix

    def _okay_to_update(self, dpkg):
        '''
        If we just uploaded a datapackage, it may be UNAVAILABLE.
        Wait until it is not in that state.
        Return the possibly more current dpkg object.
        '''
        one_tick = 1
        maxticks = 120 * 60/one_tick  # 2 hours
        total_ticks = maxticks
        pkg_id = dpkg.id
        first_time = True
        while maxticks:
            try:
                dpkg = self._b_fynn.get(pkg_id)   # state may be changing, get current
                if dpkg.state == 'UNAVAILABLE':
                    if first_time:
                        print('Waiting for upload to complete.')
                        print('For large files, this can take a long time.', flush=True)
                        first_time = False
                    maxticks -= 1
                    time.sleep(one_tick)
                    so_far = str(timedelta(seconds=total_ticks-maxticks))
                    if self.overwrite:
                        self.overwrite('\nWaited {}'.format(so_far))
                    else:
                        print('\rWaited {}'.format(so_far), flush=True, end='')
                else:
                    print('')
                    break
            except Exception as ex:
                print('Datapackage update error: {}.'.format(str(ex)))
                print('dpkg state: ', dpkg.state)
        if maxticks == 0:
            print('waiting to update timeout, results unpredictable')
        return dpkg


    @staticmethod
    def _wait_for_ready(collection):
        '''
        Wait for collection to be READY.
        Return current collection object.
        '''
        maxticks = 30
        while maxticks:
            collection.update()
            if collection.state == 'READY':
                break
            else:
                print('Collection {} not ready, waiting. . .'.format(collection.name))
                maxticks -= 1
                time.sleep(1)
        return collection


    def _create_ext(self, dpkg):
        """
        BF strips the last extension off of known types, such as .txt.
        For cases like this, use the list of sources in a dataset to
        create an extension for the ds. They only time we do not do
        this is that if the basename + ext is same as pkg name.
        cases:
           file and dataset names the same, nothing to do
           ds has one file,  result is _ext
           ds has more than one file type, result is _ext1_ext2
        """
        ret_ext = ''
        if not self._add_ext:
            return ret_ext
        for file in dpkg.files:
            _, ext = os.path.splitext(os.path.basename(file.s3_key))
            basename = os.path.basename(file.s3_key)
            if basename == dpkg.name:
                continue
            _, ext = os.path.splitext(basename)
            if ext not in ret_ext:
                ret_ext += '_' + ext[1:]
        return ret_ext

    def _name_conform_api(self, res, prefix):
        '''
        Using the api is less work. The res object has lots of info
        about what we just uploaded, such as datapackage name and id .
        '''
        for subres in res:
            pkg_id = subres[0]['package']['content']['id']
            dpkg = self._b_fynn.get(pkg_id)
            if dpkg.name in self.PROTECTED_NAMES:
                continue
            dpkg = self._okay_to_update(dpkg) #insure current and updateable
            self._pkg_rename(dpkg, prefix)


    def _name_conform_agent(self, files, collection, prefix):
        '''
        The agent returns no info about what got uploaded. All we can
        do here is get a list of the files in the current collection and
        find the one with our uploaded file name in the sources attribute.
        If an item does not have any values in that attribute, it is probably
        the one we want. We still have to wait until it is not UNAVAILABLE
        before we can rename it, so wait around for a state we can use.
        '''
        collection = self._wait_for_ready(collection)
        for file in files:
            file = os.path.basename(file)
            if file in self.PROTECTED_NAMES:
                continue
            dpkg = None
            for dpkg in collection:
                if isinstance(dpkg, Collection):
                    continue
                if not dpkg.sources: # (this is probably the one we are looking for)
                    # srcs not valid until pkg is not UNAVAILABLE, wait for it
                    dpkg = self._okay_to_update(dpkg)
                for lookup in dpkg.sources:
                    realfile = os.path.basename(lookup.s3_key)
                    if realfile == file:
                        break
                else:
                    continue
                break
            if dpkg is None:
                print('ERROR: Unexpected error: could not find the uploaded file'
                      'in a datapackage, datapackage not renamed.')
                return
            self._pkg_rename(dpkg, prefix)


    def _pkg_rename(self, dpkg, prefix):
        '''
        Common rename operations regardless of api or agent usage.
        '''
        ext = self._create_ext(dpkg)
        re_name = prefix + dpkg.name + ext
        if dpkg.name != re_name:
            print('\nRenaming ', dpkg.name, end='')
            print(' to', re_name)
            dpkg = self._okay_to_update(dpkg)
            try:
                dpkg.update(name=re_name)
            except Exception as ex:
                print('Datapackage update error: {}.'.format(str(ex)))
        else:
            print(dpkg.name, 'not renamed')

    def name_conform(self, res, files, collection, prefix):
        '''
        File(s) have been uploaded. The upload results is in res if using API,
        in files list if using agent. Make the datapackage name conform to the
        DAT-core standards. Also optinally tag on the extension as part of the
        fname if BF has removed it, which it does for file types it recognizes.
        This kills us because we have some files where the basename is the
        same, and when both of them get the extension stripped off, the rename
        fails because they have the same name. Tacking the extension text on
        make unique names.

        TODO when more than one file winds up in a dpkg, it makes sense to concatenate
        the extensions if there are only a couple of file, like:
        sub-name_name_ext1_ext2. This can get out of hand with 50 files.
        '''
        if res:
            self._name_conform_api(res, prefix)
        else:
            self._name_conform_agent(files, collection, prefix)


    def validate_profile(self):
        """
        Is the current working profile name acceptable to BF?
        """
        ret = True
        prob = ''
        try:
            self._b_fynn = Blackfynn(self._profile_name)
        except Exception as ex:
            ret = False
            prob = str(ex)
        return ret, prob


    def bf_connect(self):
        """
        Try to connect to bfynn
        """
        ret = True
        prob = ''
        self._dataset = None
        try:
            self._dataset = self._b_fynn.get_dataset(self._dataset_name)
        except Exception as ex:
            prob = str(ex)
            ret = False
        return ret, prob

    @classmethod
    def get_version(cls):
        """
        Who are we this time?
        """
        return __version__

    def setup(self):
        '''
        Prompt for info we need to upload.
        Returns dataset, csv file name.
        Does not return on fatal errors.
        '''
        # CSV File
        self._get_csv()
        if not self._csv_name:
            sys.exit('Uploading aborted.')
        if not self.chk_files_exist():
            choice = input('\nSome files are missing.\n'
                           'Do you want to continue anyway?\n'
                           'Type y for yes, anything else for no: ')
            if choice != 'y':
                sys.exit('Uploading aborted.')
        # Profile
        self.get_profile()
        is_ok, errtxt = self.validate_profile()
        if not is_ok:
            sys.exit('Bad profile or error trying to connect to ' +
                     'Blackfynn, uploading aborted.\n' + errtxt)
        # Dataset
        self._get_dataset_name()
        if not self._dataset_name:
            sys.exit('There is not a dataset name in the .csv file in row 4, column 1,\n'
                     'cannot upload, aborting program.')
        # Tag on file extension that BF removes for known file types?
        self._get_add_ext()
        # Use the blackyfynn agent?
        self._get_use_agent()
        print('Trying to connect to dataset. . .', flush=True)
        is_ok, errtxt = self.bf_connect()
        if not is_ok:
            sys.exit('Unable to connect to the dataset, uploading aborted. ' + errtxt)
        print()
        print('Dataset:        {}\nCSV file:       {}\nProfile:        {}\n'\
               'Add Extension:  '.format(
                   self._dataset_name, self._csv_name, self._profile_name), end='')
        if self._add_ext:
            print('Yes')
        else:
            print('No')
        print('Use Agent:      ', end='')
        if self._use_agent:
            print('Yes')
        else:
            print('No')

        ok2go = input('Okay to continue(y/n)? ')
        if ok2go != 'y':
            sys.exit('Aborting upload.')

    def cancel_upload(self):
        """
        The gui program can abort the upload, not so easy from cmd line (could check for
        Q keypress in the upload loop, I guess
        """
        self._stop_right_now = True

    def do_upload(self):
        '''
        Read in a csv file with from and to info and upload
        to the selected dataset on the Blackfynn site.
        Create collections (subfolders) as required
        and rename data packages (files) as required.
        '''
        top_level_name = ''
        curr_data_dir = self._dataset
        dest_name = self._dataset.name
        curr_top_dir = []
        curr_sub_dir = []
        curr_sess_dir = []
        upload_prefix = ''
        curr_sub_name = ''
        curr_sess_name = ''
        self._uploaded = 0

        print('Reading file {}'.format(self._csv_name))
        with open(self._csv_name) as csvfile:
            in_file = csv.reader(csvfile, delimiter=',')
            try:
                for row in range(self.ROWS_TO_DSET):  # skip info rows
                    next(in_file)
            except Exception as ex:
                print('Error reading row {} of {} file,\n'
                      'error is {}.'.format(row, self._csv_name, str(ex)))
                print('If you are using excel, save the file as a CSV (MS-DOS) .csv file')
            for row in in_file:
                top_name = row[self.TOP_LEVEL]
                sub_name = row[self.SUBJ]
                sess_name = row[self.SESSID]
                dest_fold = row[self.DESTFOLD]
                src_file = row[self.SRCFILE]
                # Step down into top level, subject, sample, etc.
                if top_name and not top_name.isspace():
                    top_level_name = top_name
                    curr_data_dir = self._collection_chk(self._dataset, top_level_name)
                    curr_top_dir = curr_data_dir
                    dest_name = top_level_name
                    curr_sub_name = ''
                    curr_sess_name = ''
                # Step down into instance of a subject, sample, etc.
                if sub_name and not sub_name.isspace():
                    curr_sub_name = self._get_prefix(top_level_name) + sub_name
                    dest_name = top_level_name + '/' + curr_sub_name
                    curr_data_dir = self._collection_chk(curr_top_dir, curr_sub_name)
                    curr_sub_dir = curr_data_dir
                    upload_prefix = curr_sub_name + '_'
                    curr_sess_dir = []
                    curr_sess_name = ''
                # Step down into optional session
                if sess_name and not sess_name.isspace():
                    curr_sess_name = self._get_prefix('session') + sess_name
                    dest_name = top_level_name + '/' + curr_sub_name + '/' + curr_sess_name
                    curr_data_dir = self._collection_chk(curr_sub_dir, curr_sess_name)
                    curr_sess_dir = curr_data_dir
                    upload_prefix = curr_sub_name + '_' + curr_sess_name + '_'
                # Step down into data type, anat, ephys, etc., under subject/sample/etc/dir
                if dest_fold and not dest_fold.isspace():
                    if isinstance(curr_sess_dir, Collection):
                        curr_data_dir = self._collection_chk(curr_sess_dir, dest_fold)
                    else:
                        curr_data_dir = self._collection_chk(curr_sub_dir, dest_fold)
                    dest_name = top_level_name + '/' + curr_sub_name
                    if curr_sess_name:
                        dest_name += '/' + curr_sess_name
                    dest_name += '/' + dest_fold
                if not src_file:
                    continue
                expanded_files = self._make_file_list(src_file)
                if expanded_files:
                    self._upload_list(curr_data_dir, expanded_files, upload_prefix, dest_name)
                    if self._stop_right_now:
                        self._stop_right_now = False
                        return False
        print("Uploaded " + str(self._uploaded) + " files")
        return True


def main():
    '''
    Read in a csv file with file from and to info and upload
    to the selected dataset on the Blackfynn site.
    Assumes you have python3 installed, the Blackfynn API installed, the
    Blackfynn Agent installed, and have a Blackfynn profile on the local machine
    that the Blackfynn API can access.
    '''
    print(sys.version)
    cmd_bf = UploadBlackfynn()
    print(sys.argv[0], 'Version', cmd_bf.get_version())
    cmd_bf.setup()
    cmd_bf.do_upload()
    print('\nDONE!')


if __name__ == '__main__':
    main()
