AUTOMAKE_OPTIONS= -Wno-portability

bin_PROGRAMS = 
dist_bin_SCRIPTS = upload_bfynn.py upload_bfynn_win.pyw
python_PYTHON = upload_bfynn.py upload_bfynn_win.pyw
pkgpython_PYTHON = upload_bfynn.py upload_bfynn_win.pyw
dist_pkgdata_DATA= $(ZIPNAME)
dist_doc_DATA = README COPYING LICENSE ReadmeFirst.txt ReadmeSecond.txt ChangeLog WindowsInstall.txt TEMPLATE-for-SPARC-list-of-files-to-upload.csv TEMPLATE-for-SPARC-list-of-files-to-upload.xlsx

# test files for upload testing
LOCAL_ZIPFILES = \
					  info1.txt \
                 info2.txt \
                 info3.txt \
                 info4.txt \
                 info5.txt \
                 info.txt \
                 Readme \
                 sess2.rec \
                 test1.s2cx \
                 test1.s2rx \
                 test1.smr \
                 testfile.edf \
                 testfile.daq \
                 testData.nev \
                 testData.ns2

# run out of this dir
LOCAL_ZIPWORKING = \
   WindowsInstall.txt \
   TEMPLATE-for-SPARC-list-of-files-to-upload.xlsx \
	win_upload_test.xlsx \
	win_upload_test.csv  \
	win_upload_verbose_test.xlsx \
	win_upload_verbose_test.csv \
	win_upload_test-local.xlsx \
	win_upload_test-local.csv  \
	uploadblackfynn.lnk \
   upload_bfyn_win.lnk

ZIPDIR = ./upload_blackfynn
ZIPWORKING = $(ZIPDIR)/working
ZIPFILES = $(ZIPDIR)/files
ZIPNAME = upload_blackfynn_$(VERSION).zip
BUILT_SOURCES = $(ZIPNAME)


all-am: $(ZIPNAME)
	make $(ZIPNAME)

release:
	make checkin_release
	make clean
	make all-am

zipdir:
	@mkdir -p $(ZIPDIR)
	@mkdir -p $(ZIPWORKING)
	@mkdir -p $(ZIPFILES)

$(ZIPNAME): Makefile $(python_PYTHON) $(dist_doc_DATA) $(LOCAL_ZIPFILES)
	make upd_version
	make zipdir
	cp -v -p -u $(dist_doc_DATA) $(ZIPDIR)
	cp -v -p -u $(LOCAL_ZIPWORKING) $(python_PYTHON) $(ZIPWORKING)
	cp -v -p -u $(LOCAL_ZIPFILES) $(ZIPFILES)
	zip -r $(ZIPNAME) upload_blackfynn


upd_version:
	sed -i -e "s/^__version__.*/__version__ = '$(VERSION)'/g" $(python_PYTHON)

clean:
	@rm -f ${BUILT_SOURCES} 
	@rm -f $(ZIPWORKING)/*
	@rm -f $(ZIPFILES)/*
	@rm -rf $(ZIPDIR)/*

EXTRA_DIST = debian $(ZIPDIR) 

checkin_files=$(pkgpython_PYTHON) $(EXTRA_DIST) $(dist_doc_DATA) Makefile.am configure.ac

checkin_release:
	git add $(checkin_files) && git commit -uno -S -q -m "Release files for version $(VERSION)"

checkpoint:
	git add $(checkin_files) && git commit -uno -S -q -m "checkpoint files for version $(VERSION)"

checkpoint_withcomment:
	git add $(checkin_files) && git commit -uno -S -q 

deb:
	@echo 'Making debian packages'
	make distdir &&\
	cd $(distdir) &&\
	dpkg-buildpackage -Zgzip -uc -us && \
	cd .. && \
	rm -rf $(distdir)

