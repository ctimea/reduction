"""
Full-window (no excluded lines) continuum imaging scripts.  There must be a
``to_image.json`` file in the directory this is run in.  That file is produced
by ``split_windows.py``.

You can set the following environmental variables for this script:
    EXCLUDE_7M=<boolean>
        If this parameter is set (to anything), the 7m data will not be
        included in the images if they are present.
"""

import os
import json
from metadata_tools import determine_imsize, determine_phasecenter, logprint
from tasks import tclean, exportfits, plotms
from taskinit import msmdtool
msmd = msmdtool()

imaging_root = "imaging_results"
if not os.path.exists(imaging_root):
    os.mkdir(imaging_root)

# load the list of line MSes from a file
# these are all of the individually split windows,.....
with open('to_image.json', 'r') as fh:
    to_image = json.load(fh)

for band in to_image:
    for field in to_image[band]:
        # get all spectral windows for a given band (B3 or B6) for a specified
        # field.  These were split to allow for individual line imaging.
        vis = list(map(str, [x
                             for spw in to_image[band][field]
                             for x in to_image[band][field][spw]
                            ]))

        # strip off .split
        basename = os.path.split(vis[0][:-6])[1]

        if os.getenv('EXCLUDE_7M'):
            for ms in list(vis):
                msmd.open(ms)
                if any(['CM' in x for x in msmd.antennanames()]):
                    # exclude MSes with 7m data
                    vis.remove(ms)
                msmd.close()
            suffix = '12M'
        else:
            suffix = '7M12M'

        # only need to determine the phasecenter for 1 ms, under the assumption
        # that they will all overlap.  We have to check that this assumption
        # never breaks down, though.
        coosys,racen,deccen = determine_phasecenter(ms=vis[0], field=field)
        phasecenter = "{0} {1}deg {2}deg".format(coosys, racen, deccen)
        pixscale = 0.05
        # similarly, we should only need to determine the imsize for one MS
        imsize = list(determine_imsize(ms=vis[0], field=field,
                                       phasecenter=(racen,deccen), spw=0,
                                       pixscale=pixscale))
        cellsize = ['{0}arcsec'.format(pixscale)] * 2

        contimagename = os.path.join(imaging_root, basename) + "_" + suffix


        for robust in (-2, 0, 2):
            imname = contimagename+"_robust{0}".format(robust)

            if not os.path.exists(imname+".image.tt0"):
                tclean(vis=vis,
                       field=field.encode(),
                       imagename=imname,
                       gridder='mosaic',
                       specmode='mfs',
                       phasecenter=phasecenter,
                       deconvolver='mtmfs',
                       scales=[0,3,9,27,81],
                       nterms=2,
                       outframe='LSRK',
                       veltype='radio',
                       niter=10000,
                       usemask='auto-multithresh',
                       interactive=False,
                       cell=cellsize,
                       imsize=imsize,
                       weighting='briggs',
                       robust=robust,
                       pbcor=True,
                       # do not save model; these are line data
                       savemodel='none',
                      )

                exportfits(imname+".image.tt0", imname+".image.tt0.fits")
                exportfits(imname+".image.tt0.pbcor", imname+".image.tt0.pbcor.fits")
            else:
                logprint("Skipping completed file {0}".format(imname),
                         origin='almaimf_fullcont_imaging')