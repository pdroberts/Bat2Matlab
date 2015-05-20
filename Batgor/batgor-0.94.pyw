#!/usr/bin/env python
# vim:ai ts=4 sw=4 expandtab:
# read a BATLAB PST data file


DEBUG = 0

version = "BatGor 0.94.4: Convert Batlab PST files to IGOR or MINITAB input."

gpl = """
Copyright (c) 2005,2006 by Ed Groth

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os,sys
sys.path = sys.path + [ "." ]
import wx
from math import *
import time
from StringIO import StringIO
import traceback
import random
import re
from xml.sax import saxutils 

# standout, the flexible output object!
# written by Michael Foord
# http://www.voidspace.org.uk/python/modules.shtml
# if this version of BatGor didn't ship with standout.py,
# just download standout.py and put it in the current directory
# or install it in /usr/lib/python-2.4 (linux, probably mac)
# or c:\Python24\libs (windows), or whatever your python library directory is.
#
# standout is used so I can get stack traces if the program dies in Windows.
from standout import StandOut
stout = StandOut(filename="log-batgor.txt")  #setup logging to a file
sterr = StandOut(stream='error', share=True)


# a function to xml-escape all the strings in a sequence, and return a new sequence
def xml_escape_list(strings):
    strings = (str(s) for s in strings) # make sure they're really strings :-)
    estrings = [] #escaped strings
    for string in strings:
        estring = saxutils.escape(string)
        estrings.append(estring)
    return tuple(estrings)

# constants for the wx event handler
ID_ABOUT=101
ID_OPEN=102
ID_SAVE=103
ID_SAVE_MINI=104
#ID_SAVE_RAW_INDEX=105
ID_SAVE_VOCAL_INFO=106
ID_SAVE_XML=107
ID_SAVE_XML_NOSPIKES=108
ID_BUTTON1=110
ID_EXIT=200
class ListWindow(wx.Frame):
    type_colors = { 'twotone': "cyan", 
                        'bbn': "yellow",
                        'nbn': "yellow",
                         'fm': "green", 
                        'sam': "purple", 
               'vocalization': "white",
                  'tone:auto': "orange", #tone tests which are also auto tests
                  '(default)': "grey"    #anything not otherwise listed (including single tone tests)
                  }
    def __init__(self,parent,id,title):
        self.dirname=''
        self.title = title
        self.parent = parent
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, (200,200), (520, 490),
                          style=wx.DEFAULT_FRAME_STYLE| wx.NO_FULL_REPAINT_ON_RESIZE)

        self.sizer=wx.BoxSizer(wx.VERTICAL)
        #Layout sizers
        self.SetSizer(self.sizer)

        tID = wx.NewId()
        #self.lc = wx.ListCtrl(self, tID,
        self.lc = wx.ListCtrl(self, -1,
                              style=wx.LC_REPORT 
                              | wx.BORDER_SUNKEN
                              | wx.LC_EDIT_LABELS
                              | wx.LC_SORT_ASCENDING
                              )

        self.currentItem = 0 #selected item

        self.colorkey = wx.BoxSizer(wx.HORIZONTAL) #key for colors in list control
        for testtype in sorted(ListWindow.type_colors.keys()):
            print testtype
            colortext = wx.StaticText(self, -1, " " + testtype + " ", style=wx.ALIGN_CENTRE)
            colortext.SetBackgroundColour(ListWindow.type_colors[testtype])
            self.colorkey.Add(colortext, 1, wx.EXPAND)
        self.sizer.Add(self.colorkey)

        self.lc.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.lc)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.lc)

        self.sizer.Add(self.lc, 1, wx.EXPAND)

        self.viewtest = wx.Button(self, -1, "View Selected Test ")
        #self.exporttest = wx.Button(self, -1, "Export Test")
        self.Bind(wx.EVT_BUTTON, self.OnViewTest, self.viewtest)

        self.sizer.Add(self.viewtest, 0)

        self.CreateStatusBar() # A Statusbar in the bottom of the window
        # Setting up the menu.
        filemenu= wx.Menu()
        filemenu.Append(ID_OPEN, "&Open Batlab PST file"," Open a Batlab file")
        filemenu.Append(ID_SAVE, "Export all tests to &IGOR text file"," Export an IGOR file")
        filemenu.Append(ID_SAVE_MINI, "Export selected tests to &MINITAB text file"," Export a MINITAB file")
        filemenu.Append(ID_SAVE_XML, "Export all test data as &XML text file"," Export an XML file")
        filemenu.Append(ID_SAVE_XML_NOSPIKES, "Export all test data as &XML text file (without spike data)"," Export an XML file")
#        filemenu.Append(ID_SAVE_RAW_INDEX, "Export an index to the &RAW file"," Export an index to RAW file")
        filemenu.Append(ID_SAVE_VOCAL_INFO, "Export an index of &vocal calls"," Export an index of vocal calls")
        filemenu.AppendSeparator()
        filemenu.Append(ID_ABOUT, "&About"," Author and license information")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT,"E&xit"," Terminate the program")
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        wx.EVT_MENU(self, ID_ABOUT, self.OnAbout)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, ID_OPEN, self.OnOpen)
        wx.EVT_MENU(self, ID_SAVE, self.OnSave)
        wx.EVT_MENU(self, ID_SAVE_MINI, self.OnSaveMini)
#        wx.EVT_MENU(self, ID_SAVE_RAW_INDEX, self.OnSaveRAWIndex)
        wx.EVT_MENU(self, ID_SAVE_VOCAL_INFO, self.OnSaveVocalInfo)
        wx.EVT_MENU(self, ID_SAVE_XML, self.OnSaveXML_spikes)
        wx.EVT_MENU(self, ID_SAVE_XML_NOSPIKES, self.OnSaveXML_nospikes)

        self.Show(1)
 
    def setFileID(self, fileid):
        self.fileid = fileid
        print "ListWindow.fileid: ", fileid
    def setTests(self, tests):
        self.tests = tests

        self.lc.ClearAll()
        self.lc.InsertColumn(0, "Test#", width=50)
        self.lc.InsertColumn(1, "Comment", width=180)
        self.lc.InsertColumn(2, "Date", width=140)
        self.lc.InsertColumn(3, "Traces", width=50)
        self.lc.InsertColumn(4, "Type", width=70)

        for test in self.tests:
            testnum = "%03d" % test.number
            comment = test.comment
            date = test.date
            ntraces = str(len(test.traces))
            example_stimulus = test.first_non_control_stimulus()

            index = self.lc.InsertStringItem(sys.maxint, testnum)

            self.lc.SetTextColour("black")
            self.lc.SetBackgroundColour("black")

            #self.lc.SetBackgroundColour("black")
            self.lc.SetStringItem(index, 1, comment)
            self.lc.SetStringItem(index, 2, date)
            self.lc.SetStringItem(index, 3, ntraces)
            self.lc.SetStringItem(index, 4, test.igor_testtype())
            
            #colorize the output
            if test.igor_testtype() == 'tone' and test.type == 'auto':
                #frequency tuning autotest
                self.lc.SetItemBackgroundColour(index,ListWindow.type_colors['tone:auto'])
            elif test.igor_testtype() in ListWindow.type_colors:
                self.lc.SetItemBackgroundColour(index,ListWindow.type_colors[test.igor_testtype()])
            else:
                self.lc.SetItemBackgroundColour(index,ListWindow.type_colors['(default)'])

            self.lc.SetItemData(index, int(testnum))

    def update_viewtest_label(self):
        if self.lc.GetSelectedItemCount() > 1:
            self.viewtest.SetLabel("View Selected Tests")
        else:
            self.viewtest.SetLabel("View Selected Test ")

    def OnItemDeselected(self, event):
        self.update_viewtest_label()
        event.Skip()

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
        self.update_viewtest_label()
        event.Skip()

    def OnDoubleClick(self, event):
        """view a single test after a double click"""
        if DEBUG:
            print "OnDoubleClick item %s\n" % self.lc.GetItemText(self.currentItem) 
            print "Test Selected is:", self.tests[self.currentItem] 
        tiw = TestInfoWindow(self, -1, "Test Info", self.tests[self.currentItem], self.dirname, self.filename)
        event.Skip()

    def OnViewTest(self, event):
        """view a single test after a "view test" button pressed"""
        item = -1
        while True:
            item = self.lc.GetNextItem(item, state=wx.LIST_STATE_SELECTED)
            if item == -1:
                break
            if DEBUG: print "item is selected: ", item
            tiw = TestInfoWindow(self, -1, "Test Info", self.tests[item], self.dirname, self.filename)
        return

    def OnOpen(self,e):
        """ Open a Batlab file"""
        dlg = wx.FileDialog(self, "Please Choose a Batlab .PST File", self.dirname, "", \
                            "Batlab PST files (*.pst)|*.pst|All files (*.*)|*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.ReadFile(dlg.GetDirectory(), dlg.GetFilename())
        self.SetTitle(self.title + ": " + dlg.GetFilename()) # put filename in title 
        dlg.Destroy()

    def ReadFile(self, dirname, filename):
        self.filename = filename
        self.dirname = dirname
        f = open(os.path.join(self.dirname, self.filename),'r')
        try:
            (tests, fileid) = parse(f)
        except:
            d = wx.MessageDialog(self, "Can't Read File %s!\nIs it a Batlab .PST file?\n\nFull Error: %s"
                                       % (filename, traceback.format_exc()),
                "Oh Crap", wx.OK|wx.ICON_EXCLAMATION)
            d.ShowModal()
            f.close()
            return

        if len(fileid) == 0 or len(tests) == 0:
            d = wx.MessageDialog(self, "Not much data found in file %s!\nIs it a Batlab .PST file?\n"
                                       % (filename),
                "No Data", wx.OK|wx.ICON_EXCLAMATION)
            d.ShowModal()
            
        self.setFileID(fileid)
        self.setTests(tests)
        # mark the last test with a variable so the IGOR code can step through them 
        # without causing an exception by running off the end.
        tests[-1].setlast(True) 

        # TODO: need to check for and report other errors here.
        # (most errors cause a crash which we display in a dialog box, and we
        #  have special case displays for some other errors above.  so what we
        #  need here is just a generic "sorry: unknown error, see source code"
        #  type message box.)
        f.close()


    def OnSaveXML_spikes(self, e):
        self.OnSaveXML(include_spikes=True)

    def OnSaveXML_nospikes(self, e):
        self.OnSaveXML(include_spikes=False)

    def OnSaveXML(self, include_spikes=True):
        """save an XML text file giving all relevant info from .pst file.
        Lars and I use this XML file to transfer the data into Matlab.
        Eventually it would be nice for all output to be generated from the
        XML, and have separate libraries which take XML data and save it as Igor data.
        """
        defaultname = without_extension(self.filename)
        if include_spikes:
            defaultname += '-alltests.xml'
        else:
            defaultname += '-alltests-nospikes.xml'

        path = save_file_dialog(self, self.dirname, defaultname)

        if path != None: # None means cancelled 
            try:
                f = open(path,'w')
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write("<!-- xml version of " + saxutils.escape(self.filename) + " -->\n")

                # write 
                #print "self.fileid", self.fileid
                if len(self.fileid) == 5 and self.fileid[-2] == '0' and self.fileid[-1] == '0':
                    #older versions of the batlab program didn't have the
                    #computer name or program date fields.
                    self.fileid  = self.fileid[:-2] +  2 * [ 'none(old batlab version)' ] + self.fileid[-2:]
                #print "self.fileid", self.fileid
                f.write("""
<experiment pst_filename="%s"
            date="%s"
            title="%s"
            who="%s"
            computername="%s"
            program_date="%s">\n""" % xml_escape_list(self.fileid[0:6]))

                testnum = 0
                offset = 0
                num_vocal_calls_in_file =0
                for test in self.tests:
                    testnum += 1
                    test.writeXMLtofile(f, testnum, include_spikes)

                f.write("</experiment>\n")
                f.close()
            except Exception, e:
                d = wx.MessageDialog(self, "Error Writing %s!\n%s\n" % (path, traceback.format_exc()),
                    "Oh Crap", wx.OK|wx.ICON_EXCLAMATION)
                d.ShowModal()

    def OnSaveVocalInfo(self, e):
        """save an text file giving info about vocal calls in the .pst file"""
        defaultname = without_extension(self.filename)
        defaultname += '-vocal-call-index.txt'

        path = save_file_dialog(self, self.dirname, defaultname)

        if path != None: # None means cancelled 
            try:
                f = open(path,'w')
                f.write("# vocal call locations in " + self.filename + "\n")
                f.write("# each vocal call in the pst file is listed in the format:\n")
                f.write("# [vocal_call_info] #begin section\n")
                f.write("# test_number = 11  # test number 1..N\n")
                f.write("# trace_number = 0  # trace number 0..N-1\n")
                f.write("# vocal_call_file = \"foo.call1\" # name of vocal call file. \n")
                f.write("# attenuation = 20  # attenuation in decibels\n")
                f.write("# is_reversed = 0   # 0 if normal, 1 if call is played backwards\n")
                f.write("#\n")
                f.write("# [vocal_call_info] #begin next section\n")
                f.write("# test_number = 11\n")
                f.write("# trace_number = 1\n")
                f.write("# vocal_call_file = \"c:\\path\\to\\foo2.call1\" # can be full path to file\n")
                f.write("# attenuation = 40\n")
                f.write("# is_reversed = 0\n")

                testnum = 0
                offset = 0
                num_vocal_calls_in_file =0
                for test in self.tests:
                    testnum += 1
                    tracenum = 0
                    for trace in test.traces:
                        vocal_call_file = trace.get_vocal_call_file()
                        if vocal_call_file != '':
                            f.write("\n");
                            f.write("[vocal_call_info]\n")
                            f.write("test_number = %s\n" % testnum)
                            f.write("trace_number = %s\n" % tracenum)
                            f.write("vocal_call_file = \"%s\"\n" % vocal_call_file)
                            f.write("attenuation = %s\n" % trace.stimuli[0].attenuation)
                            f.write("is_reversed = %s\n" % trace.stimuli[0].reverse_vocal_call)
                            num_vocal_calls_in_file += 1
                        tracenum += 1
                if num_vocal_calls_in_file == 0:
                    f.write("\n# FYI: I didn't find any vocal calls in %s\n" % self.filename)
                else:
                    f.write("\n# Found %d vocal calls in %s\n" % (num_vocal_calls_in_file, self.filename))

                f.close()
            except Exception, e:
                d = wx.MessageDialog(self, "Error Writing %s!\n%s\n" % (path, traceback.format_exc()),
                    "Oh Crap", wx.OK|wx.ICON_EXCLAMATION)
                d.ShowModal()

    def OnSave(self, e):
        """ Save an IGOR file"""
        defaultname = without_extension(self.filename)
        defaultname += '-pst-alltests-igor.txt'

        path = save_file_dialog(self, self.dirname, defaultname)

        if path != None: # None means cancelled 
            try:
                f = open(path,'w')
                # the folder is named after the PST file but sanitised so it can be an igor folder name
                igor_foldername = re.subn('[^a-zA-Z0-9_]','', re.subn('\.','_',self.filename)[0])[0]
                if not re.match("^[a-zA-Z]", igor_foldername):
                    # folder name must start with a letter, so we add an X if necessary
                    igor_foldername = "X" + igor_foldername
                igor_foldername = "root" + ":" + igor_foldername
                f.write("IGOR\n") #IGOR like hear name!  IGOR load file when hear IGOR!
                f.write("X NewDataFolder/O/S %s\n" % igor_foldername)
                f.write("X SetDataFolder %s\n" % igor_foldername)
                f.write(linelist2wave(self.fileid,"file_id_information") + "\n")
                for test in self.tests:
                    f.write( test.igor_format(igor_foldername) )
                f.close()
            except Exception, e:
                d = wx.MessageDialog(self, "Error Writing %s!\n%s\n" % (path, traceback.format_exc()),
                    "Oh Crap", wx.OK|wx.ICON_EXCLAMATION)
                d.ShowModal()

    def OnSaveMini(self, e):
        """ Save a MINITAB file """

        path = "test-batgor-minitab.txt"

        if path != None: # None means cancelled 
            try:
                # this is where the minitab file is written.
                f = open(path,'w')
                # first, write column headings.

                # TODO: clean me up 
                item = -1
                stats = {}
                selected_testnumbers = []
                while True:
                    item = self.lc.GetNextItem(item, state=wx.LIST_STATE_SELECTED)
                    if item == -1:
                        break

                    test = self.tests[item]
                    testnum = item + 1 #test number starting at one, to match up with lab book etc.
                    testtype = test.igor_testtype()
                    selected_testnumbers.append( testnum ) 

                    if testtype == 'tone':
                        si = test.igor_StimInfo()
                        for tnum in range(len(test.traces)):
                            # put all of the stimulus -> response info in stats[]
                            trace = test.traces[tnum]

                            # stim is a tuple so it can go in a dictionary,
                            # and the elements appear in the order we want them sorted in
                            stim = (testtype,
                                    trace.repetition_rate,
                                    si["attenuation"][tnum],
                                    si["frequency"][tnum],
                                    si["delay"][tnum],
                                    si["duration"][tnum]) 

                            #mean spike count is total spikes / presentations.
                            response = ("test_%d" % testnum, 
                                        trace.mean_spike_count())

                            #print "trace stats: ", trace.record_duration, trace.num_samples
                            if stim not in stats:
                                stats[stim] =  [ response ]
                            else:
                                stats[stim].append(response)
                                

                    elif testtype == 'twotone':
                        # build a stats[] dictionary for two tone tests, similar to above, except
                        # one difference: some data in the stimulus is in string form so 
                        # I can put two frequencies (for example) into one field.  I only want this to
                        # affect presentation and sorting, but not how it appears in the file.
                        # I'm not sure how to cram all these numbers into the column label.  
                        # 
                        # note: it's sometimes impossible to fit all of the relevant stimulus
                        # data in the name, so there's a function in the Igor procedure file
                        # called stimulus_list() that makes longer names for twotone tests.

                        #(fpairs, apairs, spairs, dpairs) = test.igor_Twotone_StimInfoPairs()
                        infopairs = test.igor_Twotone_StimInfoPairs()
                        for tnum in range(len(test.traces)):
                            trace = test.traces[tnum]

                            stim = (testtype,
                                    trace.repetition_rate,
                                    "%s_%s" % (infopairs.attenuation[2*tnum : 2*tnum+2]),
                                    "%s_%s" % (infopairs.frequency[2*tnum : 2*tnum+2]),
                                    "%s_%s" % (infopairs.delay[2*tnum : 2*tnum+2]),    #start==delay
                                    "%s_%s" % (infopairs.duration[2*tnum : 2*tnum+2]))

                            response = ("test_%d" % testnum, 
                                        trace.mean_spike_count())

                            if DEBUG: print tnum, stim, response

                            if stim not in stats:
                                stats[stim] =  [ response ]
                            else:
                                stats[stim].append(response)
                            
                    else:
                        print "not a tone or twotone test, skipping"
                        continue


                # Intersection: the stats that all the tests are in.
                inter_stats = {} 

                # Difference: the stats that not all the tests are in.
                diff_stats = {} 

                for k in stats.keys():
                    if len(stats[k]) == len(selected_testnumbers):
                        inter_stats[k] = stats[k] 
                    else:
                        diff_stats[k] = stats[k] 

         

                if DEBUG:
                    print selected_testnumbers
                    print "STATS:"
                    print "\n".join(str(x) for x in sorted(stats.items()))
                    print "INTERSECTION:"
                    print "\n".join(str(x) for x in sorted(inter_stats.items()))
                    print "DIFFERENCE:"
                    print "\n".join(str(x) for x in sorted(diff_stats.items()))

                    print "MINITAB:"
                    stims = sorted(inter_stats.keys())
                    #print "\t".join(stims)
                    for stim in stims:
                        print '"%s_rate%d_%ddB_%dhz_delay%s_duration%s"' % stim, 
                    print
                    for i in range(len(selected_testnumbers)):
                        for stim in stims:
                            print inter_stats[stim][i][2], 
                        print

                mtiw = MiniTabInstersectionWindow(self, -1, "Export this data to Minitab?",
                                                    inter_stats, diff_stats, self.dirname, self.filename)
                f.close()
            except Exception, e:
                d = wx.MessageDialog(self, "Error Writing %s!\n%s\n" % (path, traceback.format_exc()),
                    "Oh Crap", wx.OK|wx.ICON_EXCLAMATION)
                d.ShowModal()

    def OnAbout(self,e):
        d= wx.MessageDialog(self,
                            version + "\n" + gpl,
                            "About BatGor", wx.OK)
        d.ShowModal() # Shows about dialog 
        d.Destroy()   # destroy about dialog when finished.

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

class MiniTabInstersectionWindow(wx.Frame):
    def __init__(self, parent, id, title, inter, diff, dirname, filename):
        self.inter = inter
        self.diff = diff
        self.dirname = dirname
        self.filename = filename
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, (-1, -1), (700, 700), style=wx.DEFAULT_FRAME_STYLE)
                          #style=wx.DEFAULT_FRAME_STYLE| wx.NO_FULL_REPAINT_ON_RESIZE)

        self.sizer=wx.BoxSizer(wx.VERTICAL)


        # label
        self.lcilabel = wx.StaticText(self, -1, \
                            "Intersecting Trace Types (Will be Exported)",
                            (-1,-1),
                            (-1,20)) #(500,20))
        self.lcilabel.SetFont(wx.Font(12,wx.NORMAL,wx.NORMAL,wx.NORMAL))
        self.sizer.Add(self.lcilabel, 0)


        # the list control size must be set to (0,0), otherwise there's an ugly blank grey area.  go figure.
        self.lci = wx.ListCtrl(self, -1, (-1,-1), (0,0), style=wx.LC_REPORT)

        self.lci.InsertColumn(0, "Type", width=60)
        self.lci.InsertColumn(1, "Rep Rate", width=60)
        self.lci.InsertColumn(2, "Attenuation", width=70)
        self.lci.InsertColumn(3, "Frequency", width=100)
        self.lci.InsertColumn(4, "Delay", width=80)
        self.lci.InsertColumn(5, "Duration", width=80)
        self.lci.InsertColumn(6, "Responses [(test, mean spike count), ...]", width=1200)

        self.lci.SetTextColour("black")
        self.lci.SetBackgroundColour("grey")

        for k,v in sorted(self.inter.items()):
            #index = self.lci.InsertStringItem(0,k[0])
            index = self.lci.InsertStringItem(sys.maxint,k[0])
            for j in range(1,6):
                self.lci.SetStringItem(index, j, str(k[j]))
            #self.lci.SetStringItem(index, 6, str(v))
            self.lci.SetStringItem(index, 6, '[' + ', '.join([("(%s, %5.3f)" % (x[0], x[1])) for x in v]) + ']')
            self.lci.SetItemBackgroundColour(index,"green")
        self.sizer.Add(self.lci, 1, wx.EXPAND, 1)


        # label
        self.lcdlabel = wx.StaticText(self, -1, \
                            "Nonintersecting Trace Types (Will not be Exported)",
                            (-1,-1),
                            (-1,20)) #(500,20))
        self.lcdlabel.SetFont(wx.Font(12,wx.NORMAL,wx.NORMAL,wx.NORMAL))
        self.sizer.Add(self.lcdlabel, 0)

        self.lcd = wx.ListCtrl(self, -1, (-1,-1), (0,0), style=wx.LC_REPORT)

        self.lcd.InsertColumn(0, "Type", width=60)
        self.lcd.InsertColumn(1, "Rep Rate", width=60)
        self.lcd.InsertColumn(2, "Attenuation", width=70)
        self.lcd.InsertColumn(3, "Frequency", width=100)
        self.lcd.InsertColumn(4, "Delay", width=80)
        self.lcd.InsertColumn(5, "Duration", width=80)
        self.lcd.InsertColumn(6, "Responses [(test, mean spike count), ...]", width=1200)

        self.lcd.SetTextColour("black")
        self.lcd.SetBackgroundColour("grey")

        for k,v in sorted(self.diff.items()):
            index = self.lcd.InsertStringItem(sys.maxint,k[0])
            for j in range(1,6):
                self.lcd.SetStringItem(index, j, str(k[j]))
            self.lcd.SetStringItem(index, 6, '[' + ', '.join([("(%s, %5.3f)" % (x[0], x[1])) for x in v]) + ']')
            self.lcd.SetItemBackgroundColour(index,"red")
        self.sizer.Add(self.lcd, 1, wx.EXPAND, 1)

        #buttons
        self.bsizer=wx.BoxSizer(wx.HORIZONTAL) #buttons tray
        self.ok = wx.Button(self, 10, "Export the Intersection!")
        self.cancel = wx.Button(self, 20, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.ok_click, self.ok)
        self.Bind(wx.EVT_BUTTON, self.cancel_click, self.cancel)
        self.bsizer.Add(self.cancel, 0)
        self.bsizer.Add(self.ok, 0) 
        self.sizer.Add(self.bsizer, 0)

        self.SetSizer(self.sizer)
        self.Show()

    def ok_click(self,event):
        if DEBUG: print "OK"

        defaultname = self.filename 
        if defaultname[-4] == '.': #get rid of extension
            defaultname = defaultname[:-4]
        defaultname += '-pst-alltests-minitab.txt'

        path = save_file_dialog(self, self.dirname, defaultname)
        if path != None: # None means cancelled
            f = open(path,'w')
            if DEBUG: print "MINITAB:"
            stims = sorted(self.inter.keys())
            f.write('"file and test name"\t')
            for stim in stims:
                #f.write('"%s_rate%d_%ddB_%dhz_delay%s_duration%s"\t' % stim)
                # minitab doesn't like column headers longer than 31 characters, they will be truncated
                # This works OK for single tone, but not for twotone... minitab will truncate
                # the labels and I don't know what to do about it.
                #f.write('"%s%d_%ddB_%dhz_%s_%s"\t' % stim)
                f.write('"%s%s_%sdB_%shz_%s_%s"\t' % stim)
            f.write("\n")

            #for i in range(len(selected_testnumbers)):
            for i in range(len(self.inter.values()[0])):
                f.write('"%s::%s"\t' % (self.filename, self.inter[stim][i][0])) # filename & test name
                for stim in stims:
                    f.write("%s\t" % self.inter[stim][i][1]) 
                f.write("\n")

    def cancel_click(self,event):
        if DEBUG: print "CANCEL"
        self.Close(True)



class TestInfoWindow(wx.Frame):
    def __init__(self, parent, id, title, test, dirname, filename):
        self.dirname = dirname
        self.pstfilename = filename
        self.test = test
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, (-1, -1), (500, 480),
                          style=wx.DEFAULT_FRAME_STYLE| wx.NO_FULL_REPAINT_ON_RESIZE)

        self.sizer=wx.BoxSizer(wx.VERTICAL)

        #test info
        self.infobar = wx.StaticText(self, -1, \
                            "Test %s (%s), %s.    Comment: %s" \
                            % (test.number, test.type, test.date, test.comment),
                            (-1,-1),
                            (-1,20)) #(500,20))
        #self.infobar.SetFont(wx.Font(12,wx.NORMAL,wx.NORMAL,wx.NORMAL))


        self.sizer.Add(self.infobar, 0)

        self.lc = wx.ListCtrl(self, -1, (-1,-1),(500, 600),
                              style=wx.LC_REPORT 
                              | wx.BORDER_SUNKEN
                              #| wx.BORDER_NONE
                              #| wx.LC_EDIT_LABELS #don't need this AFIAK.  (commented-out Dec 19, 2005)
                              | wx.LC_SORT_ASCENDING
                              #| wx.LC_NO_HEADER
                              #| wx.LC_VRULES
                              #| wx.LC_HRULES
                              #| wx.LC_SINGLE_SEL
                              )
        self.sizer.Add(self.lc, 1, wx.EXPAND, 0)

        self.lc.InsertColumn(0, "Trace#", width=50)
        self.lc.InsertColumn(1, "Samples", width=60)
        self.lc.InsertColumn(2, "Stimulus Label", width=180)
        self.lc.InsertColumn(3, "Spikes", width=50)
        self.lc.InsertColumn(4, "Vocal Call", width=120)

        self.lc.SetTextColour("black")
        self.lc.SetBackgroundColour("grey")
        traceno = 1
        for trace in self.test.traces:
            index = self.lc.InsertStringItem(sys.maxint,"%04d" % traceno)
            self.lc.SetStringItem(index, 1, str(trace.num_samples))
            self.lc.SetStringItem(index, 2, trace.stimlabel())
            self.lc.SetStringItem(index, 3, str(trace.total_spikes()))
            self.lc.SetStringItem(index, 4, trace.get_vocal_call_file())
            traceno += 1

        self.bsizer=wx.BoxSizer(wx.HORIZONTAL) #buttons tray

        #buttons
        self.ok = wx.Button(self, 10, "OK!")
        self.Bind(wx.EVT_BUTTON, self.ok_click, self.ok)
        self.bsizer.Add(self.ok, 0) 
        self.sizer.Add(self.bsizer, 0)

        self.SetSizer(self.sizer)

        self.Show()

    def ok_click(self, event):
        if DEBUG: print "OK!"
        self.Close()


def without_extension(filename):
    dot = filename.rfind('.')
    if dot == -1:
        return filename
    else:
        return filename[0:dot]

def save_file_dialog(parentwindow, dirname, defaultname):
    """file save dialog used to save IGOR files
    dirname is the default directory to save in
    defaultname is the default file name
    returns the path (directory + file) that the user selected.
    """
    dlg = wx.FileDialog(parentwindow, "Name of IGOR file to save to?", dirname, defaultname,
                        "*.*", wx.SAVE)
    if dlg.ShowModal() == wx.ID_OK:
        savefile = dlg.GetFilename()
        savedir  = dlg.GetDirectory()
        path = os.path.join(savedir, savefile)
        fileexists = 1
        try:
            s = os.stat(path)
        except:
            fileexists = 0
        if fileexists:
            d= wx.MessageDialog(None,
                        "%s already exists!  Overwrite?\n" % savefile,
                        "Overwrite File?", wx.YES_NO | wx.NO_DEFAULT)
            if d.ShowModal() != wx.ID_YES:
                #cancelled
                dlg.Destroy()
                return None
        dlg.Destroy()
        return path
    return None


def main():
    # I want to add a batch-mode operation to the program so we can convert a bunch
    # of .pst files to igor input all at once (for example, all the .pst files under
    # a directory.)  This means I'll need to ether add some methods to the gui object to 
    # make them "scriptable", or move _all_ file output code into non-gui objects.  It would
    # probably be a better idea to have separate gui and file-output objects anyway, but
    # it would probably take less time to make the gui objects scriptable.
    #
    # Yet another option would be to add a dialog in the gui to convert all the
    # files under a directory.  Hmm...
    if len(sys.argv) < 2:
        """for testing with windows (no command line)"""
        #sys.argv = ["./pst_over_here.py", "Mouse346(DCN).pst"]
    #sys.argv = ["./pst_over_here.py", "Mouse346(DCN).pst"] #force
    try:
        filename = sys.argv[1]
    except:
        sys.stderr.write("use: ./batgor-pst.py batlab-data-file.pst\n")
        #sys.exit(1)

    #todo: add a plain command-line loader
    if 0:
        try:
            f = open(filename, "r")
        except:
            sys.stderr.write("Aborting! Can't read file %s\n" % filename)
            sys.exit(1)

        if DEBUG: print "file open", filename

    app = wx.PySimpleApp()
    # frame = ListWindow(None, -1, "Batlab PST -> IGOR text file exporter")
    frame = ListWindow(None, -1, "Batlab PST -> text file exporter")
    #frame.ReadFile(".", filename)
    app.MainLoop()


def trim_31(label):
    #trim a label to 31 characters, the maximum length igor will allow
    original = label

    # check for a label that we can handle.
    if len(label) > 30 and label.count('_') == 0:  
        print "error in trim_31(): label %s contains no underscores, so it is "
        print "impossible to trim it to 31 characters long.  This is the result of a bug"
        print "in the part of the program that generates labels, and the program needs to be fixed."
        sys.exit(1) #exit because this error could cause Igor to get confused and corrupt data.
        # todo: display a dialog box instead of just crashing.
    while len(label) > 30:
        #truncate.  we use lots of underscores so this should work fine.
        #todo:  if there are no underscores in the first 30 characters, then this would loop forever.
        #all my names have lots of underscores so this should always work.  
        label = label[:label.rfind('_')] 
    if original != label:
        label = label + 'X' #show we've changed it.
    return label


class BatlabTest:
    def __init__(self,type):
        self.type = type
        self.number = self.date = None
        self.traces = []
        self.islast = False #assume I'm not the last test
        self.comment = ""
        self.length_in_raw_file = 0
        self.offset_in_raw_file = 0

    def setcomment(self,comment):
        self.comment = comment.rstrip()
    def setnumber(self,number):
        self.number = int(number)
    def setdate(self,date):
        self.date = date
    def setlast(self,islast):
        #am I the last test in the file?
        self.islast = islast
    def addtrace(self,trace):
        self.traces.append(trace)
        # need to recalculate our length since we just added another trace.
        self.length_in_raw_file = 0
        for trace in self.traces:
            self.length_in_raw_file += trace.get_length_in_raw_file()

    def get_length_in_raw_file(self):
        # bytes this test uses in raw file
        return self.length_in_raw_file

    def set_offset_in_raw_file(self, offset):
        # bytes offset this test starts at in the raw file
        self.offset_in_raw_file = offset
        trace_offset = offset
        for trace in self.traces:
            trace.set_offset_in_raw_file(trace_offset)
            trace_offset += trace.get_length_in_raw_file()


    def get_offset_in_raw_file(self):
        return self.offset_in_raw_file


    def igor_testtype(self):
        # this is the test type for the Igor programs to use.
        # some Igor test types correspond to more than one batlab test.
        # some batlab tests have no corresponding Igor test type.
        for trace in self.traces:
            tonecount = 0
            for stimulus in trace.stimuli:
                if stimulus.istype("broad_band_noise"):
                    return "bbn" 
                if stimulus.istype("sine_wave_modulation"):
                    #print "SAM!!!", "stim.soundtype: ", stimulus.soundtype, "AMtype", stimulus.AMtype, "rate", stimulus.AMrate, "depth", stimulus.AMdepth, "dutycycle", stimulus.AMdutycycle
                    #print "stim: ", stimulus
                    return "sam" #sinosoidally amplitude modulated
                if stimulus.istype("fmsweep"):
                    return "fm" 
                if stimulus.istype("stored_vocal_call"):
                    return "vocalization" 
                if stimulus.istype("tone"):
                    tonecount += 1
            if tonecount > 1:
                return "twotone"
        #tone: the default.  It's at the end because I need to check that no 
        #traces are 2-tone before assuming its a one-tone stimulus.
        return "tone" 

    def igor_StimInfo(self):
        # these are "waves" of information on each stimulus
        # for example: info["frequency"][run] == frequency of tone.
        # (for two-tone tests please use igor_Twotone_StimInfoPairs())
        if self.igor_testtype() == 'twotone':
            sys.stdout.write("error: two tone tests have more stimuli than igor_StimInfo[1] can handle!\n"
                           + "\n".join(traceback.format_stack()))

            return {"error": [0]}
        else:
            info = { "attenuation": [],
                       "frequency": [],
                        "duration": [],
                           "delay": [],
                       "is_rising": [],
                       "rise_fall": [],
                           "phase": [],
                     "center_freq": [],
                       "bandwidth": [], 
                          "AMtype": [],
                          "AMrate": [],
                         "AMdepth": [],
                     "AMdutycycle": []   }


            for trace in self.traces:
                # control traces have len(trace.stimuli) == 0
                if len(trace.stimuli) <= 1:
                    # p is the parameter we're looking for in the stimulus
                    # if it isn't there, use a 0.
                    for p in info.keys():
                        if trace.iscontrol() or p not in trace.stimuli[0].__dict__:
                            info[ p ].append(0)
                        else:
                            info[ p ].append(trace.stimuli[0].__dict__[ p ])
                else:
                    sys.stdout.write("error: more stimuli than igor_StimInfo[2] can handle!\n"
                                    )# + "\n".join(traceback.format_stack()))
                    print "trace:", trace
                    for stimulus in trace.stimuli:
                        if stimulus.istype("tone"):
                            print "type tone"
                        else:
                            print "stim:", stimulus

            return info

    def igor_Twotone_StimInfoPairs(self):
        # for one-tone tests use igor_StimInfo() function
        #
        # these arrays each correspond to a wave of frequency (or attenuation, # etc.)
        # data.  frequency[2*run, 2*run+1] == frequency both tones in run.
        infopairs = { "attenuation": [],
                        "frequency": [],
                         "duration": [],
                            "delay": [], #(called startpairs in the output).  I misnamed this in 
                                         # an older version and now I can't change it without breaking
                                         # all the old exported files & analysis code in Igor. :-/
                           "AMtype": [],
                           "AMrate": [],
                          "AMdepth": [],
                      "AMdutycycle": []   }

        if self.igor_testtype() != 'twotone':
            sys.stdout.write("error: not a two-tone test!\n")
            #return [ ]
            return { "error": [0] }
        else:
            # insert the pair of stimulus frequencies (or pair of attenuations,
            # AMrates, etc)into the IGOR file in this order:
            #
            # (0) if there was no sound then just insert two zeros. 
            #
            # (1) if there is one frequency, the stimulus information is put in
            #     the second location, the first location is all zeros.
            #
            # (2) if there are two tones: changing frequency in first location
            #     followed by nonchanging frequency in second location (nonchanging
            #     is usually best frequency for the cell).
            #
            #     To find which frequency is changing, we count the number if
            #     different frequencies in each stimulus slot, the one that has
            #     more different frequencies is probably changing. (*)
            #
            # (*) NOTE: This is only a heuristic.  If it breaks you get to keep
            #     the pieces.  :-(  It is possible to dig the expected autotest
            #     frequencies out of the test portion of the PST file, but I
            #     don't think that would help in any practical situation,
            #     since if this method fails, it seems to me that something went
            #     seriously wrong with the PST file.

            different_frequencies = [{}, {}]
            for trace in self.traces:
                # count the number of different frequencies in each stimulus slot
                sfreqs = [ stimulus.frequency for stimulus in trace.stimuli ]
                sloud  = [ stimulus.attenuation for stimulus in trace.stimuli ]
                if len(trace.stimuli) > 1:  
                    #only count frequencies when there is more than one tone
                    for i in range(len(trace.stimuli)):
                        if DEBUG:
                            print "trace: ", self.traces.index(trace),
                            print "sloud[%d]: %s  sfreqs[%d]: %s" % (i, sloud[i], i, sfreqs[i])
                        different_frequencies[i][sfreqs[i]] = 1

            # now this deteremines the order in which we add stimulus information to the IGOR file.
            if len(different_frequencies[0]) > len(different_frequencies[1]):
                # first stimulus slot has more different frequencies
                stim_order = [0,1]
            else:
                # second stimulus slot has more different frequencies, or if they have equal number.
                # default since this order is correct in all PST files I have checked it on.
                stim_order = [1,0]

            for trace in self.traces:
                if len(trace.stimuli) == 2:
                    for j in stim_order:
                        for p in infopairs.keys():
                            if p in trace.stimuli[j].__dict__:
                                infopairs[p].append(trace.stimuli[j].__dict__[p])
                            else:
                                infopairs[p].append(0)
                elif len(trace.stimuli) == 1:
                    for p in infopairs.keys():
                        infopairs[p].append(0)
                        if p in trace.stimuli[0].__dict__:
                            infopairs[p].append(trace.stimuli[0].__dict__[p])
                        else:
                            infopairs[p].append(0)

                elif len(trace.stimuli) == 0:
                    for p in infopairs.keys():
                        infopairs[p].append(0)
                        infopairs[p].append(0)
                else:
                    sys.stdout.write("error: twotone test has more than two stimuli!\n")
                    return { "error": [0] }

            return infopairs

    def bestfrequency(self):
        """this function is valid for two-tone tests only"""
        fcount = {}
        for trace in self.traces:
            for stimulus in trace.stimuli:
                try:
                    fcount[ stimulus.frequency ] += 1
                except:
                    fcount[ stimulus.frequency ] = 1
        bestfreq = 0
        maxcount = 0
        for (freq, count) in fcount.items():
            if count > maxcount:
                bestfreq = freq
                maxcount = count
        return bestfreq

    def writeXMLtofile(self,f,testnum,include_spikes):
        f.write("""
  <test id="%s"
        comment="%s"
        date="%s"
        testtype="%s"
        offset_in_raw_file="%s"
        length_in_raw_file="%s">\n"""       \
        % xml_escape_list((testnum, self.comment, self.date, \
                           self.igor_testtype(), self.offset_in_raw_file, self.length_in_raw_file)))

        for trace in self.traces:
            trace.writeXMLtofile(f,include_spikes)

        f.write("  </test>\n")

    def igor_format(self, igor_dirname):
        string = ""
        foldername = "%s:test_%s" % (igor_dirname, self.number)
        #folder save/restore doesn't work.  why not?
        #print "X String old_data_folder = GetDataFolder(1)"
        string += "X NewDataFolder/O/S %s\n" % foldername
        string += "X SetDataFolder %s\n" % foldername
        #this is for the igor file format
        string += """WAVES/T test_metadata test_metadata_labels
BEGIN
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
END
""" %  (self.type, "test_type", self.number, "test_number", self.date, "test_date",
        self.comment, "test_comment", len(self.traces), "number_of_traces_in_test",
        self.igor_testtype(), "igor_test_type", self.islast, "i_am_the_last_test")

        gens = []
        #make a list of generators that spit out one line of data at a time
        #then for each line, combine the output of the generators into columns of data.
        for trace in self.traces:
            gen = trace.igor_format_gen() #generator
            gens.append(gen)
       
        n_wavenames = []
        t_wavenames = []
        # gather the wave name headers.
        for gen in gens:
            next = gen.next()
            n_wavenames.append(next[0])
            t_wavenames.append(next[1])

        # make the "list of waves" text waves
        string += "\nWAVES/T n_wavenames t_wavenames\nBEGIN\n"
        for (n,t) in zip(n_wavenames, t_wavenames):
            string += '\t"%s"\t"%s"\n' % (n,t)
        string += "END\n"

        # add record duration and repetition rate info here (from BatlabTrace)
        string += "\nWAVES record_duration repetition_rate num_samples"
        string += "\nBEGIN\n"
        for trace in self.traces:
            string += "\t%s\t%s\t%s\n" % (trace.record_duration, trace.repetition_rate, trace.num_samples)
        string += "END\n"

        string += 'X String testtype = \"' + self.igor_testtype() + '\" \n'

        if self.igor_testtype() == 'twotone':
            # (again, the delay of both tones is called startpairs instead of delaypairs because I mistyped it in
            #  an earlier version of this program and now I can't change it without breaking old files and
            #  the analysis code.)
            string += "\nWAVES frequencypairs attenuationpairs startpairs durationpairs AMtypepairs AMratepairs AMdepthpairs AMdutycyclepairs"
            string += "\nBEGIN\n"
            infopairs = self.igor_Twotone_StimInfoPairs()
            for i in range(0, len(infopairs['frequency'])): #(they should all be the same length as frequency)
                for p in ( "frequency", "attenuation", "delay", "duration", \
                           "AMtype", "AMrate", "AMdepth", "AMdutycycle"):
                    string += "\t%s" % infopairs[p][i]
                string += "\n"
            string += "END\n"
        else:
            # print a "wave" header with each of the attributes of the stimuli (eg: frequency, attenuation)
            # then print a bunch of columns with the data for each stimulus (eg: 24000, 36)
            # the info is in a dictionary because it can vary for different test types.
            info = self.igor_StimInfo()
            infokeys = sorted(info.keys())
            string += ("\nWAVES" + " %s" * len(infokeys)) % tuple(infokeys)
            string += "\nBEGIN\n"
            for i in range(0, len(info[infokeys[0]])): 
                for k in infokeys:
                    string += "\t%s" % info[k][i]
                string += "\n"
            string += "END\n"

        if len(n_wavenames) > 0: # check for at least one wave before writing IGOR WAVE block
            string += "\nWAVES "
            # print the run data wave name headers.
            for n,t in zip(n_wavenames, t_wavenames):
                string += "%s %s " % (n,t)
            string += "\nBEGIN\n"
            while True:
                columns = []
                rowallzero = True
                for gen in gens:
                    next = gen.next()
                    if next != (0,0):
                        rowallzero = False
                    columns.append(tuple(next))
                if rowallzero:
                    break
                #print "columns", columns
                for (n,t) in columns:
                    #print column
                    #string += "%s\t%s\t" % (n,t)
                    string += "\t%s\t%s" % (n,t)
                string += "\n"
            string += "END\n"

        #string += "X SetDataFolder old_data_folder\n" #if only folder save/restore worked  :-(
        return string

    def first_non_control_stimulus(self):
        for trace in self.traces:
            #just grab an example trace that isn't a control
            #so the user has some idea what this is
            string = ""
            if not trace.iscontrol():
                #string += "first non-control stimulus:\n" 
                for stim in trace.stimuli:
                    string += str(stim)
                return string
        else:
            #string += "all trace stimuli are control\n" 
            return "control only"

    def __str__(self):
        #something like this to be used in GUI
        string = """BatlabTest(
    type = %s
    number = %s
    date = %s
    comment = %s
    traces = %s
""" % (self.type, self.number, self.date, self.comment, len(self.traces))
        
        string += self.first_non_control_stimulus() + "\n"
        string += ")\n"
        return string

class Stimulus:
    types = {
        1: "tone",
        2: "fmsweep",
        3: "synthesized_batsound",  #todo
        4: "amsound",               #what is this?  it isn't AM modulation AFAICT
        5: "broad_band_noise",
        6: "narrow_band_noise",
        7: "click",                 #todo
        8: "stored_vocal_call",     #partially works
        9: "high_pass_noise",       #todo
        10: "low_pass_noise",       #todo
        11: "sine_wave_modulation",
        12: "square_wave_modulation", #todo, not used
    }
    #wave names in IGOR are limited to 31 characters.
    #so we have short names for when we export the data.
    shortnames = {
        1: "",  #tone is the default, so no label for tone.
        2: "fm",
        3: "synth",
        4: "am",
        5: "bbn",
        6: "nbn",
        7: "click",
        8: "voc",
        9: "hpn",
        10: "lpn",
        11: "sin",
        12: "sqr",
    }

    def istype(self, type):
        # will throw KeyError if the type is not on the list.
        # then you need to fix the caller to use a type on the list.
        if DEBUG: print "self.soundtype", self.soundtype, "type", type, "self.AMtype", self.AMtype
        if self.types[self.soundtype] == type:
            return True #its a major stimulus type.
        elif self.AMtype > 0 and self.types[self.AMtype] == type: 
            return True #its a modulation type. usually SAM (sine wave modulation).
        else:
            return False

    def __init__(self,stimulusline):
        (self.soundtype, self.attenuation, self.duration, self.delay) = stimulusline[1:5]
        self.vocal_call_file = "" #default no vocal call file.
        amstart = False #all sound types can be AM modulated, the AM info starts here
        if self.soundtype == 1: #pure tone
            amstart = 8
            (self.frequency, self.rise_fall, self.phase) = stimulusline[5:8]
            self.frequency = int(self.frequency)
        elif self.soundtype == 2: #FM sweep
            amstart = 10
            (self.center_freq, self.bandwidth, self.is_rising, self.rise_fall, self.phase) = stimulusline[5:10]
        elif self.soundtype == 5: #broadband noise
            amstart = 7
            (self.rise_fall, self.phase) = stimulusline[5:7]
        elif self.soundtype == 6: #narrowband noise
            amstart = 9
            (self.center_freq, self.bandwidth, self.rise_fall, self.phase) = stimulusline[5:9]
        elif self.soundtype == 8: #stored vocal call
            #TODO:
            amstart = 21 # where does AM start?
            # what other variables do we care about.
            # file name, sample type (rate), start time, attenuation, duration, delay
            #self.reverse_vocal_call = stimulusline[6]
            self.reverse_vocal_call = stimulusline[5]
            self.vocal_call_file = stimulusline[20]
            print "found vocal call %s reverse status %d" % (self.vocal_call_file, self.reverse_vocal_call)
        else:
            #just memorize it, let the user make sense of it
            #xxx: this is just asking for trouble? 
            #consider removing this.  real issue is lack of meaningful error reporting.
            #the raw data is not useful for anything except debugging
            self.raw = stimulusline[:]
        if amstart:
            try:
                (self.AMtype, self.AMrate, self.AMdepth, \
                 self.AMdutycycle) = stimulusline[amstart:amstart+4]
            except: #old data with no AM, or some bug.
                (self.AMtype, self.AMrate, self.AMdepth, \
                 self.AMdutycycle) = [0,0,0,0]
                 #= [None,None,None,None]

    def __str__(self):
        string = ""
        if self.soundtype in self.types:
            string += "type = %s\n" % self.types[self.soundtype]
            if self.AMtype == 12: #sine wave modulated
                string += "sine wave modulation: rate = %s depth = %s dutycycle = %s\n" \
                % (self.AMrate, self.AMdepth, self.AMdutycycle)
            if self.AMtype == 13: #square wave modulated
                string += "square wave modulation: rate = %s depth = %s dutycycle = %s\n" \
                % (self.AMrate, self.AMdepth, self.AMdutycycle)
        if self.soundtype == 1: #pure tone
            string += "attenuation = %s duration = %s delay = %s frequency = %s rise_fall = %s phase = %s\n" \
            % (self.attenuation, self.duration, self.delay, \
               self.frequency, self.rise_fall, self.phase)
        elif self.soundtype == 2: #FM sweep
            string += "center_freq = %s bandwidth = %s is_rising = %s rise_fall = %s phase = %s\n" \
            % (self.center_freq, self.bandwidth, self.is_rising, self.rise_fall, self.phase)
        elif self.soundtype == 5: #broadband noise
            string += "rise_fall = %s phase = %s\n" \
            % (self.rise_fall, self.phase)
        elif self.soundtype == 6: #narrowband noise
            string += "center_freq = %s bandwidth = %s rise_fall = %s phase = %s\n" \
            % (self.center_freq, self.bandwidth, self.rise_fall, self.phase)
        elif self.soundtype == 8: #stored vocal call noise
            string += "vocal_call_file = %s reverse_vocal_call = %s\n" \
            % (self.vocal_call_file, self.reverse_vocal_call)
        else:
            string += "(raw stimulus info, I don't know what it means) " + str(self.raw) + "\n"
        return string

    def writeXMLtofile(self,f):
        f.write('      <stimulus soundtype="%s"\n' % saxutils.escape(str(self.soundtype)))

        if self.soundtype in self.types:
            f.write('                soundtype_name="%s"\n' % saxutils.escape(str(self.types[self.soundtype])))
            f.write('                AMtype="%s"\n' % saxutils.escape(str(self.AMtype)))

            if self.AMtype == 12: #sine wave modulated
                f.write('                AMtype_name="%s"\n' % "sin")
            if self.AMtype == 13: #square wave modulated
                f.write('                AMtype_name="%s"\n' % "sqr")

            f.write('                AMrate="%s"\n' % saxutils.escape(str(self.AMrate)))
            f.write('                AMdepth="%s"\n' % saxutils.escape(str(self.AMdepth)))
            f.write('                AMdutycycle="%s"\n' % saxutils.escape(str(self.AMdutycycle)))

        if self.soundtype == 1: #pure tone
            f.write(('                attenuation="%s"\n' +   \
                     '                duration="%s"\n' +      \
                     '                delay="%s"\n' +         \
                     '                frequency="%s"\n' +     \
                     '                rise_fall="%s"\n' +     \
                     '                phase="%s"')          \
            % xml_escape_list((self.attenuation, self.duration, \
                               self.delay, self.frequency, self.rise_fall, self.phase)))

        elif self.soundtype == 2: #FM sweep
            f.write(('                center_freq="%s"\n' +   \
                     '                bandwidth="%s"\n' +     \
                     '                is_rising="%s"\n' +     \
                     '                rise_fall="%s"\n' +     \
                     '                phase="%s"')          \
            % xml_escape_list((self.center_freq, self.bandwidth,  \
                               self.is_rising, self.rise_fall, self.phase)))

        elif self.soundtype == 5: #broadband noise
            f.write(('                rise_fall="%s"\n' +     \
                     '                phase="%s"')          \
            % xml_escape_list((self.rise_fall, self.phase)))

        elif self.soundtype == 6: #narrowband noise
            f.write(('                center_freq="%s"\n' +   \
                     '                bandwidth="%s"\n' +     \
                     '                rise_fall="%s"\n' +     \
                     '                phase="%s"')          \
            % xml_escape_list((self.center_freq, self.bandwidth, self.rise_fall, self.phase)))

        elif self.soundtype == 8: #stored vocal call noise
            f.write(('                attenuation="%s"\n' +   \
                     '                duration="%s"\n' +      \
                     '                delay="%s"\n' +         \
                     '                vocal_call_file="%s"\n' +    \
                     '                reverse_vocal_call="%s"')
            % xml_escape_list((self.attenuation, self.duration, self.delay, 
                               self.vocal_call_file, self.reverse_vocal_call)))

        else:
            f.write('                error_unknown_stimulus_type="sorry,dude!"')
        f.write(">\n")
        f.write('      </stimulus>\n')

    def label(self):
        # bug/todo you can't have any periods (.) in the wave names
        # so, we have to either truncate/round values, or put them in
        # in units that will not round (for example, 1000 * value)
        if self.soundtype in self.types:
            if self.soundtype == 1:
                #tone is the default, no label for tone.  this is because of the Igor 31-char limit.
                #since tones are often combined, a tone description should be under 15 characters
                #I wonder if there is a way around this restriction?
                label = "" 
            else:
                label = "_%s" % self.shortnames[self.soundtype]
            if self.AMtype == 12: #sine wave modulated
                label += "_sin_%s_%s_%s" % (self.AMrate, self.AMdepth, self.AMdutycycle)
            if self.AMtype == 13: #square wave modulated
                label += "_sqr_%s_%s_%s" % (self.AMrate, self.AMdepth, self.AMdutycycle)
        else:
            #do default case here
            label += "(raw stimulus info, I don't know what it means) " + str(self.raw) + ""
            return label

        #Christine says she never uses the phase: we don't bother putting phase in the label
        #phase only makes sense for binaural sound (two speakers at the same time) for 
        #testing how the animal determines directionality
        label += "_%sdB" % self.attenuation
        if self.soundtype == 1: #pure tone
            if self.frequency % 1000 == 0:
                label += "_%dk" % (self.frequency/1000)
            else:
                label += "_%dhz" % self.frequency
            if abs(self.delay - 10.0) > 0.00001:
                label += "%sD" % int(self.delay)
            if abs(self.duration - 100.0) > 0.00001:
                label += "%sL" % int(self.duration) #duration = length

        elif self.soundtype == 2: #FM sweep
            if self.center_freq % 1000 == 0:
                label += "_f%dk" % (self.center_freq/1000)
            else:
                label += "_f%d" % self.center_freq
            if self.bandwidth % 1000 == 0:
                label += "_w%dk" % (self.bandwidth/1000)
            else:
                label += "_w%d" % self.bandwidth
            if self.is_rising:
                label += "_u" #rising/upsweep
            else:
                label += "_d" #falling/downsweep
                #label += "_r%s"
                     #% (self.is_rising)

        elif self.soundtype == 5: #broadband noise
            pass #no extra data required
            #label += "_rf%sus" % rise_fall_integer_microseconds

        elif self.soundtype == 6: #narrowband noise
            if self.center_freq % 1000 == 0:
                label += "_f%dk" % (self.center_freq/1000)
            else:
                label += "_f%d" % self.center_freq
            if self.bandwidth % 1000 == 0:
                label += "_w%dk" % (self.bandwidth/1000)
            else:
                label += "_w%d" % self.bandwidth

        else:
            #do another default case here. 
            #TODO: in theory, we should have a case for each sound type supported by batlab.
            pass
        #print "LABEL generated is", label
        return label
        

class BatlabTrace:
    def __init__(self, record_vars, runnum, control=False, soundtype=None):
        #num_samples is the number of stiumulus presentations
        (self.num_samples, self.samplerate_da, self.samplerate_type, \
         self.samplerate_ad, self.record_duration, self.repetition_rate, \
         self.display_duration, self.invert_raw_data_status, self.binwidth, \
         self.stats_start, self.stats_end) = record_vars[0:11]

        self.runnum = runnum #run number
        self.control = control
        self.soundtype = soundtype

        # calculate the size in bytes of the spike recording in the raw file.
        runs_per_trace = self.num_samples
        record_duration_per_run = self.record_duration
        ADC_samplerate = self.samplerate_ad
        ADC_samplesize = 2 # always 16 bit samples for our hardware 
        self.length_in_raw_file = (runs_per_trace * record_duration_per_run \
                                  * ADC_samplerate * ADC_samplesize /1000)
        self.offset_in_raw_file = 0

        self.spikes = []
        self.stimuli = []

    def get_length_in_raw_file(self):
        # bytes this trace uses in the raw file
        return self.length_in_raw_file

    def set_offset_in_raw_file(self, offset):
        # bytes offset this trace starts at in the raw file
        self.offset_in_raw_file = offset

    def get_offset_in_raw_file(self):
        # bytes offset this trace starts at in the raw file
        return self.offset_in_raw_file

    def add_discriminator_vars(self, discriminator_vars):
        #discriminator variables are in the third line of the trace parameters
        #but we create the BatlabTrace when we get the first line.  so we add 
        #the discriminator_vars when the parser gets to the third line.

        #print "discriminator_vars:", discriminator_vars

        #spike_enhancer_power_value is the exponent the voltage is raised to 
        #when the spike enhancer is turned on
        (self.level_detector_status, self.window_detector_status, \
         self.level_voltage, self.window_voltage, self.peak_detector_status, \
         self.spike_enhancer_status, self.spike_enhancer_power_value) = discriminator_vars

    def mean_spike_count(self):
        """mean spike count is total spikes / presentations."""
        return float(self.total_spikes()) / self.num_samples

    def iscontrol(self):
        return self.control

    def addstimulus(self,stimulusline):
        stimulus = Stimulus(stimulusline)
        self.stimuli.append(stimulus)

    def addspike(self,spikedata):
        if spikedata[0] == len(spikedata[1:]):
            self.spikes.append(spikedata[1:])
        else:
            print "invalid spike data", spikedata
            print "the file is corrupt or there is a bug in this program."

    def get_vocal_call_file(self):
        if len(self.stimuli) < 1:
            return ""
        else:
            return self.stimuli[0].vocal_call_file

    def stimlabel(self):
        label = ""
        if len(self.stimuli) == 0:
            label = "_control" 
        else:
            for stimulus in self.stimuli:
                label += stimulus.label()
        label = ("_%d" % self.runnum) + label
        return label

    def total_spikes(self):
        t_spikes = 0
        for spiketrain in self.spikes:
            t_spikes += len(spiketrain)
        return t_spikes

    # f is the file object.  if include_spikes is true, write spike times
    def writeXMLtofile(self,f,include_spikes):
        f.write("""
    <trace run_number="%s"
           offset_in_raw_file="%s"
           length_in_raw_file="%s"
           num_samples="%s"
           samplerate_da="%s"
           samplerate_type="%s"
           samplerate_ad="%s"
           record_duration="%s"
           repetition_rate="%s"
           display_duration="%s"
           invert_raw_data_status="%s"
           binwidth="%s"
           stats_start="%s"
           stats_end="%s"
           is_control="%s"
           soundtype="%s"
           level_detector_status="%s"
           window_detector_status="%s"
           level_voltage="%s"
           window_voltage="%s"
           peak_detector_status="%s"
           spike_enhancer_status="%s"
           spike_enhancer_power_value="%s">\n""" % tuple((self.runnum, 
            self.offset_in_raw_file, self.length_in_raw_file,
            self.num_samples, self.samplerate_da, self.samplerate_type,           ##recording variables
            self.samplerate_ad, self.record_duration, self.repetition_rate,
            self.display_duration, self.invert_raw_data_status, self.binwidth,
            self.stats_start, self.stats_end, self.control, self.soundtype,
            self.level_detector_status, self.window_detector_status,              ##discriminator variables
            self.level_voltage, self.window_voltage, self.peak_detector_status,
            self.spike_enhancer_status, self.spike_enhancer_power_value)))

        for stimulus in self.stimuli:
            stimulus.writeXMLtofile(f)

        if include_spikes:
            f.write('      <spikedata units="presentation_number,spike_time_in_microseconds">\n')

            presentation = 0
            for spiketrain in self.spikes:
                presentation += 1
                f.write("        ") #indentation
                for spiketime in spiketrain:
                    f.write("%s %s " % (presentation, spiketime))
                f.write("\n")

            f.write("      </spikedata>\n")

        f.write("    </trace>\n")

    def igor_format(self, igor_dirname):
        string = ""
        foldername = "%s:test_%s" % (igor_dirname, self.number)
        #folder save/restore doesn't work.  why not?
        #print "X String old_data_folder = GetDataFolder(1)"
        string += "X NewDataFolder/O/S %s\n" % foldername
        string += "X SetDataFolder %s\n" % foldername
        #this is for the igor file format
        string += """WAVES/T test_metadata test_metadata_labels
BEGIN
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
\t"%s"\t"%s"
END
""" %  (self.type, "test_type", self.number, "test_number", self.date, "test_date",
        self.comment, "test_comment", len(self.traces), "number_of_traces_in_test",
        self.igor_testtype(), "igor_test_type", self.islast, "i_am_the_last_test")

    def igor_format_gen(self):
        #return trace information in IGOR format

        label = self.stimlabel()
        yield (trim_31("n" + label), trim_31("t" + label))

        presentation = 0
        for spiketrain in self.spikes:
            #since zero means "no data" for batlab, the presentation number starts at 1
            presentation += 1 
            #if len(spiketrain) == 0:
            #    stringval +=  "0 0 "
            for spike in spiketrain:
                yield (presentation, spike / self.binwidth)

        while True:
            yield (0,0)

    def __str__(self):
        stringval =  """BatlabTrace(
    num_samples = %s
    samplerate_da = %s
    samplerate_type = %s
    samplerate_ad = %s
    record_duration = %s
    repetition_rate = %s
    display_duration = %s
    invert_raw_data_status = %s
    binwidth = %s
    stats_start = %s
    stats_end = %s
""" % (self.num_samples, self.samplerate_da, self.samplerate_type, \
       self.samplerate_ad, self.record_duration, self.repetition_rate, \
       self.display_duration, self.invert_raw_data_status, self.binwidth, \
       self.stats_start, self.stats_end)
        if len(self.stimuli) == 0:
            stringval += "stimulus: no stimulus (control)\n" 
        label = ""
        for stimulus in self.stimuli:
            stringval += "stimulus: " + str(stimulus) + "\n"
            label += stimulus.label()
        if label == "":
            label = "control"
        stringval += "label: " + label + "\n"
        stringval += "number of presentations: %d\n" % len(self.spikes)
        presentation = 0
        for spiketrain in self.spikes:
            #since zero means "no data" for batlab, we start the presentation number at 1
            presentation += 1 
            if len(spiketrain) == 0:
                stringval +=  "0 0 "
            for spike in spiketrain:
                stringval +=  "%d %s " % (presentation, spike / self.binwidth)
            stringval += "\n"
        stringval += ")\n"
        return stringval

#convert a list of lines into an IGOR wave of text.
#lines should not have trailing newlines.  spaces are OK.
def linelist2wave(ll, wavelabel):
    wave = "WAVES/T/O %s\nBEGIN\n" % wavelabel
    for l in ll:
        #remove double quotes because of IGOR syntax rules for text waves
        l = "".join(char for char in l if char != '"')
        wave += '\t"%s"\n' % l
    wave += "END\n"
    return wave

# I highly recommend reading the code and comments from Batlab.cpp in the
# batlab source code, and/or the "Help -> Help on Program Topics -> Source Code
# Information" in Batlab, otherwise this parser will probably look pretty confusing.
# It is kind of similar to a top-down LL(1) parser, but terminates and returns all
# the info it could find about the tests, when it gets to the end of the file.
def parse(f):
    tests = []
    fileid = [] #array of the lines of FileID information
    state = 'id_info'
    lnum = 0 #line number in the current section

    for line in f:
        # read the line and find out what state we're in.
        # transitions:
        #  id_info    -> testparam
        #  testparam  -> comment_or_traceparam 
        #  traceparam -> spikedata
        #  spikedata  -> comment_or_traceparam
        #  comment_or_traceparam -> comment
        #  comment_or_traceparam -> traceparam
        #  comment    -> testparam
        (token, data, extra) = lex(line)

        if DEBUG:
            print "before transition:", state, token,data,extra
            
        if state == 'id_info' and token == '<endsection>':
            state = 'testparam'
            lnum = 0
            continue #skip this line, it's just syntax

        elif state == 'testparam' and token == '<endsection>':
            state = 'comment_or_traceparam' #some aborted tests have no traces
            lnum = 0
            continue #skip this line, it's just syntax

        elif state == 'traceparam' and token == '<endsection>':
            state = 'spikedata'
            lnum = 0
            continue #skip this line, it's just syntax

        elif state == 'spikedata' and token == '<endsection>':
            state = 'comment_or_traceparam'
            lnum = 0
            continue #skip this line, it's just syntax
            
        elif state == 'comment_or_traceparam':
            if token == '<endsection>':
                state = 'comment'
                lnum = 0
                continue #skip this line, it's just syntax

            else:
                state = 'traceparam'
                lnum = 0
                #don't skip this line, it's trace parameters


        if DEBUG:
            print "after transition:", lnum, state

        # now take the state we're in and the line data and figure out what it
        # means, then stuff the data into an array of BatlabTest() objects called tests[]
        # keeping track of the current test number in testnum.
        # some objects are accessed directly without using accessor functions, I don't do anything
        # too fancy and I hope this doesn't cause a readability problem.  It might be a good
        # idea to change the code to use accessors.
        if state == 'id_info':
            fileid.append(line.rstrip())

        if state == 'comment':
            # don't try parsing comments, just copy the line
            tests[-1].setcomment(line)
            state = 'testparam'
            #print "comment", line
            continue

        elif state == 'testparam':
            if lnum == 0:
                type = extra
                tests.append(BatlabTest(type))
                if DEBUG: print tests[-1]
                if DEBUG: print "data", data

            if lnum == 1:
                testnum = data[0]
                testdate = " ".join(str(x) for x in data[1:])
                tests[-1].setnumber(testnum)
                tests[-1].setdate(testdate)
                if DEBUG: print tests[-1]
                #print "type", type
                #print "testnum",testnum
                #print "testdate",testdate

        elif state == 'traceparam':
            if lnum == 0:
                #record variables
                if DEBUG: print "tests[-1]", tests[-1]
                trace = BatlabTrace(data, 1+len(tests[-1].traces), control=True, soundtype=None)
                if DEBUG:
                    print "num_samples", trace.num_samples
                    print "binwidth", trace.binwidth
                tests[-1].addtrace(trace)
                
            if lnum == 2:
                #level discriminator variables
                tests[-1].traces[-1].add_discriminator_vars(data)

            # token is almost always a numberlist but will be a paramaterlist for a vocal call since
            # vocal calls include the file name.
            if lnum >= 4 and token == '<numberlist>' or token == '<parameterlist>':
                if extra[1] >= 2: #number of floats
                    #we might not know exactly what it is, but if it has this much
                    #data, it must be some kind of stimulus, and therefore this cannot
                    #be a control trace.
                    trace = tests[-1].traces[-1]
                    trace.control = False
                    (on, soundtype) = data[0:2]
                    if on:
                        #the speaker is on (probably.)
                        #I haven't seen an example of "left speaker on" so
                        #this probably won't work with left speakers.
                        #TODO: get an example file that uses the left speaker and test
                        trace.addstimulus(data)
                        
        elif state == 'spikedata':
            #print "tests[-1]", tests[-1]
            trace = tests[-1].traces[-1]
            trace.addspike(data)
            #if tests[-1].traces[-1].control:
            #    print "control"
            "make soundtype etc part of an object and modify that"
            #if tests[-1].traces[-1].soundtype == 1:
                #print "tone spike data", data
            if DEBUG: print trace

        lnum += 1

    offset = 0
    for test in tests:
        test.set_offset_in_raw_file(offset)
        offset += test.get_length_in_raw_file()
    return (tests,fileid)
            

# lex(line): look at a .pst file line and return what kind of line it is, and
# the data in the line.  
#
# token types:
#   <begintest> the start of a new test section
#   <endsection> the end of the last section, also returns what the previous section type was
#   <textline> a line with text that we can't sort into any other category, most likely a comment or something
#   <parameterlist> a line that starts with a number but contains both numbers and text.  
#   <numberlist> a line that contains floating-point and (possibly) integer numbers
#   <intlist> a line that contains only integers
#
# The tokens that are returned by lex() are for each line can be used to parse
# the file in a manner similar to the parser for a compiler, complicated
# slightly by the fact that there is no formal grammar.  Which means I use a
# couple of "fudge factor" rules.  If you need to modify this code, the best
# way is to read this code alongside the .pst file-reading and -writing code in
# Batlab.cpp.  Make sure you have a recent copy of the source code as the format can 
# change slightly between versions.  I sometimes found it helpful  when writing
# this to compare the token type retured by lex() with the input line, and make
# sure everything was being recognized correctly.
#
# The odds are good that this code will stop working sometime in the future, as
# the batlab file format keeps on evolving.  I include the date of the batlab
# _program_ that wrote the pst file in the exported Igor file, so you at least
# have the option to revert to an older version of batlab that writes files
# compatible with this program  until you get things sorted out.  With enough
# patience, I am also sure that this program can be modified to read new
# versions of the .pst file, if you have questions feel free to email me and
# I'll try to help if I can.  Ed Groth 2006-01-03
#
def lex(line):
    #get rid of space and newline chars at the end of the line
    line = line.rstrip()



    #print "line",line
    #we check the length first since a comment line can be completely empty
    if len(line) == 0 or line[0].isalpha():  
        #we think it's a text line
        if line.endswith(" Test"):
            extra = None
            if "Single" in line:
                extra = 'single'
            if "Auto" in line:
                extra = 'auto'
            return ('<begintest>', line, extra)

        if line[0:3] == 'End':
            extra = None
            if line.find("trace parameters") >= 0:
                extra = 'traceparams'
            if line.find("test parameters") >= 0:
                extra = 'testparams'
            if line.find("spike data") >= 0:
                extra = 'spike'
            if line.find("auto test") >= 0:
                extra = 'test'
            if line.find("ID") >= 0:
                extra = 'ID'
            return ('<endsection>', line, extra)

        return ('<textline>', line, None)
    else:
        #looks like numbers
        #we make a list even though there might be only one item
        ints = 0    #number that can be parsed as int
        floats = 0  #number that can't be parsed as int
        words = 0   #can't be parsed as int or float
        array = []


        #Jun 14, 2006
        #correct batlab bug where it inserts two zeros in a row " 00 " should be " 0 0 "
        #found for example in "bat 7b.pst"
        pos_00 = line.find(" 00 ")
        if pos_00 != -1:
            line = line[:pos_00+2] + " " + line[pos_00+2:]

        for thingy in line.split():
            try:
                array.append( int(thingy) )
                ints += 1
                continue
            except ValueError:
                pass
            try:
                array.append( float(thingy) )
                floats += 1
                continue
            except ValueError:
                array.append( thingy )
                words += 1
        if words > 0:
            return('<parameterlist>', array, [ints, floats, words])
        elif floats > 0:
            return('<numberlist>', array, [ints, floats, words])
        else:
            return('<intlist>', array, [ints, floats, words])



if __name__ == '__main__':
    try: 
        main()
    except Exception, e:
        # This code is here so we print tracebacks to the log file.
        # It copied from the StandOut web page.  If we didn't do this and
        # an error occured, the console windows would disappear taking the 
        # traceback with it! 
        f = StringIO()
        traceback.print_exc(file = f)
        sys.stderr.write(f.getvalue() + '\n')
    stout.close()
    sterr.close()

