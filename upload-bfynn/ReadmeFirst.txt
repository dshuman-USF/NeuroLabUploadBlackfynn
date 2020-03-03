Feb 27, 2019
The zip file contains a Python command line utility that we wrote that uploads
our files to the Blackfynn site. We later added a windows wrapper around the
command line code. It uses the Blackfynn Python API.

We think it may be useful to others.

At the time of this writing, the current file is:

upload_blackfynn_1.0.10

The problem many are encountering is that there is a mismatch between how labs
organize and name their files locally and the organization of folders and files
in datasets on the Blackfynn site.

A solution that some seem to have used is to reorganize and rename things
locally. A lot of effort has gone into allowing entire folder/file hierarchies
to be uploaded via browser drag and drop. This seems to assume that the
structure and naming conventions have been adopted locally.

We took a different approach. We created a spreadsheet that defines the
structure we want on the Blackfynn site and then we list the files we want
uploaded to that structure. This spreadsheet becomes the input to our Python
program.

It is easier to understand this if you unzip the zip file and look at some of
the example spreadsheets.

The upload program reads the spreadsheet file, creates folders on the Blackfynn
site as required, uploads the files, and then renames them to conform to the
naming conventions. We do not have to make any changes to our local folders and
file names.

File name wild cards are supported. For example, if you have a folder with 500
.jpg files in it, you can have all of the files uploaded with a single entry in
the spreadsheet path\filename cell, like so:

C:\folder1\folder2\*.jpg

If a set of files must be uploaded as a group in a single upload operation, use
brackets in the path\filename cell, like so:

[C:\folder1\folder2\file1,C:\folder1\folder2\file2, c:\folder1\folder2\file3]

To get started, do the following:

1. Download the upload_bfynn_LATEST_VERSION file. Unzip it in the C:\ drive of
   your PC. Note that the upload processing zips the zip file, so you have to
   unzip it twice, once to get the .zip file inside the .zip file, then unzip
   it to get the contents.

2. Read the ReadmeSecond.txt file that is in C:\upload_blackfynn.

3. Proceed from there.


