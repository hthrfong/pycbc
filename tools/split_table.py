#!/usr/bin/env python
# $Id: tmplt_bank.py,v 1.6 2006/07/03 23:26:06 duncan Exp $

import time
import os
import sys
 
from optparse import OptionParser

from glue import lal
from glue import segments
from glue import segmentsUtils
from glue import gpstime

import glue.pipeline
import glue.utils

from glue.ligolw import ligolw
from glue.ligolw import table
from glue.ligolw import lsctables
from glue.ligolw import utils as ligolw_utils
from glue.ligolw.utils import process as ligolw_process
from glue.segmentdb import segmentdb_utils
from glue import pidfile as pidfile
from glue import git_version
from scipy.interpolate import interp1d
from numpy import loadtxt
from numpy import random
 
__author__  = "Alex Nitz"

PROGRAM_NAME = os.path.abspath(sys.argv[0])

params =  {'text.usetex': True }
 
### option parsing ###

parser = OptionParser(
    version = git_version.verbose_msg,
    usage   = "%prog [OPTIONS]",
    description = "Creates a template bank and writes it to XML." )

parser.add_option('-n', '--num', metavar='SAMPLES', help='number of templates in the output banks', type=int)
parser.add_option("-t", "--tmplt-bank", metavar='file', help='template bank to split')
parser.add_option("-V", "--verbose", action="store_true", help="print extra debugging information", default=False )
parser.add_option("-e", "--prefix",  help="print extra debugging information" )
parser.add_option("--sort-mchirp",action="store_true",default=False)
parser.add_option("--random-sort",action="store_true",default=False)

options, argv_frame_files = parser.parse_args()

if options.sort_mchirp and options.random_sort:
  print "You can't sort by Mchirp *and* randomly, dumbass!"

#print options.named


#print options.named
indoc = ligolw_utils.load_filename(options.tmplt_bank, options.verbose)

try:
  template_bank_table = table.get_table(indoc, lsctables.SnglInspiralTable.tableName)
  tabletype = lsctables.SnglInspiralTable
except:
  template_bank_table = table.get_table(indoc, lsctables.SimInspiralTable.tableName)
  tabletype = lsctables.SimInspiralTable


#print tabletype
length = len(template_bank_table)
num_files = int(round(length/options.num+.5))

def mchirp_sort(x,y):
    mc1,e1 = pycbc.mass1_mass2_to_mchirp_eta(x.mass1,x.mass2)
    mc2,e2 = pycbc.mass1_mass2_to_mchirp_eta(y.mass1,y.mass2)
    return cmp(mc1,mc2)

tt = template_bank_table
if options.sort_mchirp:
    print " SORTING"
    tt = sorted(template_bank_table,cmp=mchirp_sort)

if options.random_sort:
    random.shuffle(template_bank_table)

for num in range(num_files):

    # create a blank xml document and add the process id
    outdoc = ligolw.Document()
    outdoc.appendChild(ligolw.LIGO_LW())

    proc_id = ligolw_process.register_to_xmldoc(outdoc, 
                    PROGRAM_NAME, options.__dict__, ifos=["G1"],
                    version=git_version.id, cvs_repository=git_version.branch,
                    cvs_entry_time=git_version.date).process_id


    sngl_inspiral_table = lsctables.New(tabletype,columns=template_bank_table.columnnames)
    outdoc.childNodes[0].appendChild(sngl_inspiral_table)

    for i in range(options.num):
        try:
           row = tt.pop()
           sngl_inspiral_table.append(row) 
        except IndexError:
            break
    
    # write the xml doc to disk
    proctable = table.get_table(outdoc, lsctables.ProcessTable.tableName)
    proctable[0].end_time = gpstime.GpsSecondsFromPyUTC(time.time())

    outname = options.prefix + str(num) + '.xml'
    ligolw_utils.write_filename(outdoc, outname)

print num_files    
sys.exit(int(num_files))