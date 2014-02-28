# Copyright (C) 2013  Ian Harry
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#

"""
This module is responsible for setting up the matched-filtering stage of ahope
workflows. For details about this module and its capabilities see here:
https://ldas-jobs.ligo.caltech.edu/~cbc/docs/pycbc/NOTYETCREATED.html
"""

from __future__ import division

import os
from pycbc.ahope.ahope_utils import * 
from pycbc.ahope.jobsetup_utils import *

def setup_matchedfltr_workflow(workflow, science_segs, datafind_outs,
                               tmplt_banks, output_dir=None,
                               injection_file=None, tags=[]):
    '''
    This function aims to be the gateway for setting up a set of matched-filter
    jobs in an ahope workflow. This function is intended to support multiple
    different ways/codes that could be used for doing this. For now the only
    supported sub-module is one that runs the matched-filtering by setting up
    a serious of matched-filtering jobs, from one executable, to create
    matched-filter triggers covering the full range of science times for which
    there is data and a template bank file.

    Parameters
    -----------
    Workflow : ahope.Workflow
        The ahope workflow instance that the coincidence jobs will be added to.
    science_segs : ifo-keyed dictionary of glue.segments.segmentlist instances
        The list of times that are being analysed in this workflow. 
    datafind_outs : ahope.AhopeFileList
        An AhopeFileList of the datafind files that are needed to obtain the
        data used in the analysis.
    tmplt_banks : ahope.AhopeFileList
        An AhopeFileList of the template bank files that will serve as input
        in this stage.
    output_dir : path
        The directory in which output will be stored.
    injection_file : ahope.AhopeFile, optional (default=None)
        If given the file containing the simulation file to be sent to these
        jobs on the command line. If not given no file will be sent.
    tags : list of strings (optional, default = [])
        A list of the tagging strings that will be used for all jobs created
        by this call to the workflow. An example might be ['BNSINJECTIONS'] or
        ['NOINJECTIONANALYSIS']. This will be used in output names.
        
    Returns
    -------
    inspiral_outs : ahope.AhopeFileList
        A list of output files written by this stage. This *will not* contain
        any intermediate products produced within this stage of the workflow.
        If you require access to any intermediate products produced at this
        stage you can call the various sub-functions directly.
    '''
    logging.info("Entering matched-filtering setup module.")
    make_analysis_dir(output_dir)
    cp = workflow.cp

    # Parse for options in .ini file
    mfltrMethod = cp.get_opt_tags("ahope-matchedfilter", "matchedfilter-method",
                                  tags)

    # Could have a number of choices here
    if mfltrMethod == "WORKFLOW_INDEPENDENT_IFOS":
        logging.info("Adding matched-filter jobs to workflow.")
        if cp.has_option_tags("ahope-matchedfilter",
                              "matchedfilter-link-to-tmpltbank", tags):
            if not cp.has_option_tags("ahope-tmpltbank",
                              "tmpltbank-link-to-matchedfilter", tags):
                errMsg = "If using matchedfilter-link-to-tmpltbank, you should "
                errMsg = "also use tmpltbank-link-to-matchedfilter."
                logging.warn(errMsg)
            linkToTmpltbank = True
    
        inspiral_outs = setup_matchedfltr_dax_generated(workflow, science_segs, 
                                      datafind_outs, tmplt_banks, output_dir,
                                      injection_file=injection_file, tags=tags,
                                      link_to_tmpltbank=linkToTmpltbank)
    else:
        errMsg = "Matched filter method not recognized. Must be one of "
        errMsg += "WORKFLOW_INDEPENDENT_IFOS (currently only one option)."
        raise ValueError(errMsg)

    logging.info("Leaving matched-filtering setup module.")    
    return inspiral_outs

def setup_matchedfltr_dax_generated(workflow, science_segs, datafind_outs,
                                    tmplt_banks, output_dir,
                                    injection_file=None,
                                    tags=[], link_to_tmpltbank=False):
    '''
    Setup matched-filter jobs that are generated as part of the ahope workflow.
    This
    module can support any matched-filter code that is similar in principle to
    lalapps_inspiral, but for new codes some additions are needed to define
    Executable and Job sub-classes (see jobutils.py).

    Parameters
    -----------
    Workflow : hope.Workflow
        The ahope workflow instance that the coincidence jobs will be added to.
    science_segs : ifo-keyed dictionary of glue.segments.segmentlist instances
        The list of times that are being analysed in this workflow. 
    datafind_outs : ahope.AhopeFileList
        An AhopeFileList of the datafind files that are needed to obtain the
        data used in the analysis.
    tmplt_banks : ahope.AhopeFileList
        An AhopeFileList of the template bank files that will serve as input
        in this stage.
    output_dir : path
        The directory in which output will be stored.
    injection_file : ahope.AhopeFile, optional (default=None)
        If given the file containing the simulation file to be sent to these
        jobs on the command line. If not given no file will be sent.
    tags : list of strings (optional, default = [])
        A list of the tagging strings that will be used for all jobs created
        by this call to the workflow. An example might be ['BNSINJECTIONS'] or
        ['NOINJECTIONANALYSIS']. This will be used in output names.
    link_to_tmpltbank : boolean, optional (default=True)
        If this option is given, the job valid_times will be altered so that there
        will be one inspiral file for every template bank and they will cover the
        same time span. Note that this option must also be given during template
        bank generation to be meaningful.
        
    Returns
    -------
    inspiral_outs : ahope.AhopeFileList
        A list of output files written by this stage. This *will not* contain
        any intermediate products produced within this stage of the workflow.
        If you require access to any intermediate products produced at this
        stage you can call the various sub-functions directly.
    '''
    # Need to get the exe to figure out what sections are analysed, what is
    # discarded etc. This should *not* be hardcoded, so using a new executable
    # will require a bit of effort here .... 

    cp = workflow.cp
    ifos = science_segs.keys()
    match_fltr_exe = os.path.basename(cp.get('executables','inspiral'))
    # Select the appropriate class
    exe_instance = select_matchedfilterjob_instance(match_fltr_exe, 'inspiral')

    if link_to_tmpltbank:
        # Use this to ensure that inspiral and tmpltbank jobs overlap. This
        # means that there will be 1 inspiral job for every 1 tmpltbank and
        # the data read in by both will overlap as much as possible. (If you
        # ask the template bank jobs to use 2000s of data for PSD estimation
        # and the matched-filter jobs to use 4000s, you will end up with
        # twice as many matched-filter jobs that still use 4000s to estimate a
        # PSD but then only generate triggers in the 2000s of data that the
        # template bank jobs ran on.
        tmpltbank_exe = os.path.basename(cp.get('executables', 'tmpltbank'))
        link_exe_instance = select_tmpltbankjob_instance(tmpltbank_exe, 
                                                        'tmpltbank')
    else:
        link_exe_instance = None

    # Set up class for holding the banks
    inspiral_outs = AhopeFileList([])

    # Matched-filtering is done independently for different ifos, but might not be!
    # If we want to use multi-detector matched-filtering or something similar to this
    # it would probably require a new module
    for ifo in ifos:
        job_instance = exe_instance.create_job(workflow.cp, ifo, output_dir, 
                                               injection_file=injection_file, 
                                               tags=tags)
        if link_exe_instance:
            link_job_instance = link_exe_instance.create_job(cp, ifo, \
                        output_dir, tags=tags)
        else:
            link_job_instance = None

        sngl_ifo_job_setup(workflow, ifo, inspiral_outs, job_instance, 
                           science_segs[ifo], datafind_outs, output_dir,
                           parents=tmplt_banks, 
                           link_job_instance=link_job_instance,
                           allow_overlap=False)
    return inspiral_outs
