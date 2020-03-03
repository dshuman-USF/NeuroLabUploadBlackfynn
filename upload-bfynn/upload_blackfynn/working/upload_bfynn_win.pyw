#!/usr/bin/python3
"""
This is a run-in-a-window wrapper around update_bfynn.py.
You can still run that module from a command line, but this
makes things a bit easier. It also removes the restriction that
the that module must be run from the dir that the .csv files are in.

Copyright (c) 2019 by Kendall F. Morris
kmorris5@.usf.edu
License: GPLv3 or later.
Maintainer: Dale Shuman
dshuman@.usf.edu
Fri 12 Jul 2019 08:59:19 AM EDT
"""

__version__ = '1.0.17'

from tkinter import Tk
from tkinter import filedialog as fdlg
from tkinter import messagebox as mbox
from tkinter import Button
from tkinter import Radiobutton
from tkinter import Checkbutton
from tkinter import scrolledtext
from tkinter import Label
from tkinter import IntVar
from tkinter import PhotoImage
from tkinter import END, DISABLED, NORMAL, RIGHT, WORD
import os
import sys
import upload_bfynn as bfc


# this has to exactly match the text in the help string.
BOLD1 = 'TEMPLATE-for-SPARC-list-of-files-to-upload.xlsx'

HELP_TEXT = (
    '\nThis program uploads files to a Blackfynn SPARC dataset.\n\n',
    'It uses the structure and names in a .csv file to:\n\n',
    '1. Connect to an existing dataset.\n',
    '2. Create collections if required.\n',
    '3. Upload your files to datapackages in collections.\n',
    '4. Renames the datapackages to conform to the SPARC BIDS-based naming conventions.\n\n',
    'It does not make any changes to your directories or files.\n\n',
    'See: TEMPLATE-for-SPARC-list-of-files-to-upload.xlsx for how to create the csv file.\n\n',
    'Click on the Select CSV File button to pick a csv file.\n\n',
    'Select the Blackfynn profile you want to use. These are your log-in credentials.\n\n',
    'When uploading a known file type, Blackfynn removes the file extension.\n',
    'For example, if you upload "myfile.txt", the dataset will be\n',
    'name "myfile". If you have several files with the same base name but different\n'
    'known extensions, such as "myfile.txt" and "myfile.csv", the datasets \n'
    'would have the same name, so the second dataset will be named "myfile (1)".\n'
    'If you check the Append Extension If Removed checkbox,\n',
    'the file extension will be added to the dataset name. For example,\n',
    '"myfile.txt" will be renamed "myfile_txt", and "myfile.csv" will be \n'
    'renamed "myfile_csv". The names are now unique, so there is no\n'
    'duplicate name issue. Note that the BIDS prefixes will also be added\n'
    'to the dataset name.\n\n',
    'If you are uploading very large files that take more than an hour\n',
    'to upload, check the Use Blackfynn Agent. Otherwise, leave it unchecked.\n',
    'It takes a bit longer to use the Agent and, of course, it has to be installed.\n\n',
    'Stopping an upload only takes effect after the current file upload has completed.\n\n',
    'Problems? Save the text to a file and email it to dshuman@usf.edu.\n'
    )


class UploadBfynnWin:
    """
    Create and manage a top level window, and call on upload_bfynn.py functions
    to get the job done.
    """
    def __init__(self, master):
        """
        Create the window.
        """
        self._upl_bf = bfc.UploadBlackfynn()
        self._master = master
        self._prof = IntVar()
        self._prof.set(0)
        self._profile = ''
        self._dset_name = ''
        self._add_ext = IntVar()
        self._add_ext.set(1)
        self._use_agent = IntVar()
        self._use_agent.set(0)
        self._ui_ctl = {}
        self._create_gui()
        self._upl_bf.set_overwrite(self.overwrite)


    def _create_gui(self):
        '''
        Set up the tkinter window and controls
        '''
        _version = self._upl_bf.get_version()
        self._master.title('Upload Files To Blackfynn Version ' + _version)
        self._master.geometry('1024x800')
        self._ui_ctl['sel'] = Button(self._master, text='Select CSV File', command=self._selectf)
        self._ui_ctl['start'] = Button(self._master, text='Start Upload', command=self._upload,
                                       state=DISABLED)
        self._ui_ctl['stop'] = Button(self._master, text='Stop Upload', command=self._abort,
                                      state=DISABLED)
        self._ui_ctl['save'] = Button(self._master, text='Save Text To File', command=self._save)
        self._ui_ctl['clear'] = Button(self._master, text='Clear Text', command=self._clear)
        self._ui_ctl['help'] = Button(self._master, text='Help', command=self._help)
        self._ui_ctl['close'] = Button(self._master, text='Quit', command=self._quit)
        self._ui_ctl['radios'] = []
        self._ui_ctl['checks'] = []
        self._ui_ctl['chatterbox'] = scrolledtext.ScrolledText(self._master, wrap=WORD)

        self._ui_ctl['sel'].grid(row=0, column=0, padx=5, pady=8, sticky='W')
        self._ui_ctl['start'].grid(row=0, column=1, padx=5, pady=8, sticky='W')
        self._ui_ctl['stop'].grid(row=0, column=2, padx=5, pady=8, sticky='W')
        self._ui_ctl['save'].grid(row=0, column=3, padx=5, pady=8, sticky='W')
        self._ui_ctl['clear'].grid(row=0, column=4, padx=5, pady=8, sticky='W')
        self._ui_ctl['help'].grid(row=0, column=5, padx=5, pady=8, sticky='W')
        self._ui_ctl['close'].grid(row=0, column=7, padx=5, pady=8, sticky='W')
        profile_list = self._upl_bf.get_profile_list()
        if not profile_list:  # this is fatal
            mbox.showerror('FATAL ERROR: NO PROFILE',
                           'Cannot find a Blackfynn profile on this system. '
                           'You need to use the bfAgent or bf program to create'
                           'a profile.'
                           '\nSee: https://developer.blackfynn.io/agent/'
                           'index.html\nClick on OK to exit the program.')
            sys.exit('')
        Label(self._master, text='Current Profile:', justify=RIGHT).grid(column=0, row=1)
        for val, prof in enumerate(profile_list):
            self._ui_ctl['radios'].append(Radiobutton(self._master, text=prof, padx=5, pady=5,
                                                      variable=self._prof, value=val))
        num_radio = 1  # these can vary, start on this row
        for prof in self._ui_ctl['radios']:
            prof.grid(row=num_radio, column=1, sticky='W')
            num_radio += 1
        ctl1 = Checkbutton(self._master, text='Append Extension If Removed',
                           padx=5, pady=5, variable=self._add_ext)
        self._ui_ctl['checks'].append(ctl1)
        ctl2 = Checkbutton(self._master, text='Use Blackfynn Agent', padx=5, pady=5,
                           variable=self._use_agent)
        self._ui_ctl['checks'].append(ctl2)

        num_check = 1
        for opt in self._ui_ctl['checks']:
            opt.grid(columnspan=2, row=num_check, column=2, sticky='W')
            num_check += 1
        chatter_row = max(num_radio, num_check)
        self._ui_ctl['chatterbox'].grid(row=chatter_row, column=0, columnspan=8,
                                        sticky='NSEW', padx=10, pady=10)
        self._ui_ctl['chatterbox'].bind('<Key>', lambda _: 'break') # set r/o
        self._master.grid_rowconfigure(num_radio, weight=1)
        self._master.grid_columnconfigure(0, weight=0)
        self._master.grid_columnconfigure(1, weight=0)
        self._master.grid_columnconfigure(2, weight=0)
        self._master.grid_columnconfigure(3, weight=0)
        self._master.grid_columnconfigure(4, weight=0)
        self._master.grid_columnconfigure(5, weight=0)
        self._master.grid_columnconfigure(6, weight=0)
        self._master.grid_columnconfigure(7, weight=1)
        self._master.grid_rowconfigure(chatter_row, weight=255)


    def _selectf(self):
        """
        Need to select and validate a .csv file
        """
        currdir = os.getcwd()
        csv_name = fdlg.askopenfilename(initialdir=currdir,
                                        title="Select file",
                                        filetypes=(('csv files', '*.csv'),))
        if csv_name:
            self._ui_ctl['chatterbox'].insert(END, 'Selected ' + csv_name+'\n')
            good_csv = True
            self._upl_bf.set_csv(csv_name)
            self._dset_name = self._upl_bf.curr_dataset()
            if not self._dset_name:
                mbox.showerror('DATASET NAME ERROR',
                               'There is not a dataset name in the .csv file,'
                               'cannot upload.')
                good_csv = False
            if good_csv:
                got_files = self._upl_bf.chk_files_exist()
                if not got_files:
                    if not mbox.askyesno('MISSING PATHS OR FILES', 'Some files are missing.\n'
                                         'Do you want to continue anyway?'):
                        good_csv = False
            if good_csv:
                self.write('\nUsing Dataset ' + self._dset_name + '\n')
                self._ui_ctl['start'].config(state=NORMAL)
                self._ui_ctl['stop'].config(state=DISABLED)
            else:
                self._ui_ctl['start'].config(state=DISABLED)
                self._ui_ctl['stop'].config(state=DISABLED)


    def _clear(self):
        """
        Clear out the text
        """
        self._ui_ctl['chatterbox'].delete('1.0', END)


    def _upload(self):
        """
        What we are here for
        """
        self._profile = self._ui_ctl['radios'][self._prof.get()].cget('text')
        self._upl_bf.set_profile(self._profile)
        self._upl_bf.set_add_ext(self._add_ext.get())
        self._upl_bf.set_use_agent(self._use_agent.get())
        is_ok, errmsg = self._upl_bf.validate_profile()
        if not is_ok:
            errtxt = ('Bad profile or error trying to connect to '
                      'Blackfynn, uploading aborted. ' + errmsg)
            mbox.showerror('PROFILE ERROR', errtxt)
            self.write(errtxt)
            return
        self.write('Profile appears to be good.\n', flush=True)
        self.write('Trying to connect to dataset ' + self._dset_name + '. . .')
        is_ok, errmsg = self._upl_bf.bf_connect()
        if not is_ok:
            errtxt = 'Unable to connect to the dataset, uploading aborted. ' + '\n' + errmsg
            self.write('\n' + errtxt)
            mbox.showerror('CONNECTION ERROR', errtxt)
            return
        self.write('Connected.\n\n', flush=True)
        self._ui_ctl['stop'].config(state=NORMAL)
        self._ui_ctl['start'].config(state=DISABLED)
        self._ui_ctl['close'].config(state=DISABLED)
        self._ui_ctl['sel'].config(state=DISABLED)
        self._ui_ctl['clear'].config(state=DISABLED)
        self._ui_ctl['help'].config(state=DISABLED)
        self._ui_ctl['save'].config(state=DISABLED)
        if self._upl_bf.do_upload():
            self.write('Upload complete.\n')
        else:
            self.write('Upload cancelled.\n', flush=True)
        self._ui_ctl['sel'].config(state=NORMAL)
        self._ui_ctl['start'].config(state=NORMAL)
        self._ui_ctl['close'].config(state=NORMAL)
        self._ui_ctl['clear'].config(state=NORMAL)
        self._ui_ctl['help'].config(state=NORMAL)
        self._ui_ctl['save'].config(state=NORMAL)
        self._ui_ctl['stop'].config(state=DISABLED)


    def _abort(self):
        """
        Kill the upload in progress
        """
        self._upl_bf.cancel_upload()
        self._ui_ctl['sel'].config(state=NORMAL)
        self._ui_ctl['start'].config(state=NORMAL)
        self._ui_ctl['close'].config(state=NORMAL)
        self._ui_ctl['stop'].config(state=DISABLED)
        self._ui_ctl['clear'].config(state=NORMAL)
        self._ui_ctl['help'].config(state=NORMAL)
        self._ui_ctl['save'].config(state=NORMAL)


    def _save(self):
        """
        Save text to a file
        """
        try:
            save_name = fdlg.asksaveasfile(title='Save Window Text To File',
                                           filetypes=[("text files", ".txt")],
                                           defaultextension='.txt')
            if save_name:
                if not save_name.name.endswith('.txt'):
                    save_name += '.txt'
                txt = self._ui_ctl['chatterbox'].get(1.0, END)
                save_name.write(txt)
        except EnvironmentError as ex:
            print('error is {}.'.format(str(ex)))
        else:
            if save_name:
                save_name.close()


    def _help(self):
        """
        Explain it to them
        """
        txt = self._ui_ctl['chatterbox']
        txt.tag_configure('boldme', font='helvetica 10 bold italic')
        for info in HELP_TEXT:
            self._ui_ctl['chatterbox'].insert(END, info)
        start = txt.search(BOLD1, 1.0, stopindex=END)
        if start:
            end = '{}+{}c'.format(start, len(BOLD1))
            txt.tag_add('boldme', start, end)
        self._ui_ctl['chatterbox'].see(END)


    def _quit(self):
        """
        Bye
        """
        self._master.quit()


    def write(self, text, flush=False):
        """
        stdout redirected here
        The \r char is not handled correctly by the widget, it prints
        garbage chars, remove it. Also detect and ignore the cursor movement cmds.
        The text widget is remarkably difficult to turn into a terminal that
        things want because there is no overwrite mode, just add text mode and the
        idea of where the 'end' is seems flexible. Use overwrite to overwrite
        the last line.
        """
        if text.find('\r') >= 0:
            text = text.replace('\r', '')
        if text and text[0] == '\033' and text[1] == '[':
            return
        self._ui_ctl['chatterbox'].insert(END, text)
        self._ui_ctl['chatterbox'].see(END)
        if flush:
            self.flush()

    def overwrite(self, text):
        '''
        This is a callback from the upload bfyn object to
        erase the last line and overwrite it. Used mainly
        when waiting for time to pass.
        '''
        self._ui_ctl['chatterbox'].delete('end-1c linestart', 'end')
        self._ui_ctl['chatterbox'].insert(END, text)
        self._ui_ctl['chatterbox'].see(END)
        self.flush()


    def flush(self):
        """
        Required for stdout redirect
        """
        self._master.update()   # run event loop


# this is a simple .gif icon in base64 format
ICON = """
R0lGODlhQABAAMIBAAAAADxayIB4eP///zxayDxayDxayDxayCH5BAEKAAQALAAAAABAAEAAAAP+\nSLrc/jDKSau9OOvNu/9gKI5kaZ5oqq4sB7Qh8MKePNObjXf6nss+je0WtAyLlyPS2FtSBFCoUwId\nWK3SaHSnFRAE1zBWPPC2qmEweZ02p9TsKzyOVc3pcrpbM3jq8WViexcDAX0Rd2Nyc1ppcg2AVwGG\nhw13iY5xcFILk56foKCVCpdtglGKbG6hrKyjiWBqslWbpY8KrbmfDIx5WGhlaLWBdbi6uTe2ZMK9\ngmEzx61EmMPEy81XM0Pb3JNAvMup4ZjWVkQUAAHnpKbh7oqJ6xPyX5liANTBsNkkePinkQbQ48EG\nyK9y/k4AIHNjIcKEKLg1cBiH28AWFO9dLGIdceOUjyBDihxJsqTJkyhTqlzJsqXLlzBjypypMgEA\nOw==
"""

def main():
    """
    Top End
    """
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    root = Tk()
    up_gui = UploadBfynnWin(root)
    show_icon = PhotoImage(data=ICON)
    root.iconphoto(True, show_icon)
    if len(sys.argv) > 1 and sys.argv[1] == '-d': # debugging in spyder, print to console
        pass
    else:
        sys.stdout = up_gui
        sys.stderr = up_gui
    root.mainloop()
    sys.stdout = save_stdout
    sys.stderr = save_stderr

if __name__ == '__main__':
    main()
